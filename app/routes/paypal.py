"""PayPal payment routes."""

from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify, current_app, session
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.services.paypal import paypal_service
from datetime import datetime, timedelta
import logging

# Create blueprint
paypal_bp = Blueprint('paypal', __name__)

@paypal_bp.route('/pricing')
def pricing():
    """Pricing page."""
    if not paypal_service.is_configured():
        flash('Payment system is not available at the moment.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    plans = paypal_service.get_all_plans()
    user_features = current_user.get_subscription_features() if current_user.is_authenticated else {}
    
    return render_template('paypal/pricing.html',
                         plans=plans,
                         user_features=user_features,
                         paypal_configured=paypal_service.is_configured())

@paypal_bp.route('/subscribe/<tier>')
@login_required
def subscribe(tier):
    """Start subscription process."""
    if not paypal_service.is_configured():
        flash('Payment system is not available at the moment.', 'warning')
        return redirect(url_for('paypal.pricing'))
    
    if tier not in ['premium', 'pro']:
        flash('Invalid subscription tier.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Check if user can start trial
    if current_user.can_start_trial():
        # Start trial directly
        if current_user.start_trial(tier):
            flash(f'🎉 Your {tier.title()} trial has started! You have 14 days to explore all premium features.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Unable to start trial. Please contact support.', 'error')
            return redirect(url_for('paypal.pricing'))
    
    # Create PayPal subscription
    plan = paypal_service.create_subscription_plan(tier)
    if not plan:
        flash('Unable to create subscription plan. Please try again.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    subscription = paypal_service.create_subscription(plan['id'], current_user.id)
    if not subscription:
        flash('Unable to create subscription. Please try again.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Get approval URL
    approval_url = None
    for link in subscription.get('links', []):
        if link['rel'] == 'approve':
            approval_url = link['href']
            break
    
    if not approval_url:
        flash('Unable to process payment. Please try again.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Store subscription ID in session for verification
    session['pending_subscription_id'] = subscription['id']
    session['pending_tier'] = tier
    
    return redirect(approval_url)

@paypal_bp.route('/success')
@login_required
def success():
    """Handle successful subscription."""
    subscription_id = request.args.get('subscription_id') or session.get('pending_subscription_id')
    tier = session.get('pending_tier')
    
    if not subscription_id or not tier:
        flash('Invalid subscription response.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Get subscription details from PayPal
    subscription_details = paypal_service.get_subscription_details(subscription_id)
    if not subscription_details:
        flash('Unable to verify subscription. Please contact support.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Check subscription status
    status = subscription_details.get('status')
    if status == 'ACTIVE':
        # Upgrade user subscription
        if current_user.upgrade_subscription(tier, subscription_id):
            flash(f'🎉 Congratulations! Your {tier.title()} subscription is now active!', 'success')
            
            # Clear session
            session.pop('pending_subscription_id', None)
            session.pop('pending_tier', None)
            
            return redirect(url_for('main.dashboard'))
        else:
            flash('Unable to activate subscription. Please contact support.', 'error')
    else:
        flash(f'Subscription status: {status}. Please complete the payment process.', 'warning')
    
    return redirect(url_for('paypal.pricing'))

@paypal_bp.route('/cancel')
@login_required
def cancel():
    """Handle cancelled subscription."""
    # Clear session
    session.pop('pending_subscription_id', None)
    session.pop('pending_tier', None)
    
    flash('Subscription process was cancelled. You can try again anytime.', 'info')
    return redirect(url_for('paypal.pricing'))

@paypal_bp.route('/payment/success')
@login_required
def payment_success():
    """Handle successful one-time payment."""
    order_id = request.args.get('token')
    
    if not order_id:
        flash('Invalid payment response.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Capture payment
    payment_details = paypal_service.capture_payment(order_id)
    if not payment_details:
        flash('Unable to verify payment. Please contact support.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    # Check payment status
    status = payment_details.get('status')
    if status == 'COMPLETED':
        # Upgrade user subscription (one-time payment for 1 month)
        if current_user.upgrade_subscription('premium'):
            flash('🎉 Payment successful! Your premium subscription is now active for 1 month.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Payment successful but unable to activate subscription. Please contact support.', 'warning')
    else:
        flash(f'Payment status: {status}. Please complete the payment process.', 'warning')
    
    return redirect(url_for('paypal.pricing'))

@paypal_bp.route('/payment/cancel')
@login_required
def payment_cancel():
    """Handle cancelled one-time payment."""
    flash('Payment process was cancelled. You can try again anytime.', 'info')
    return redirect(url_for('paypal.pricing'))

@paypal_bp.route('/manage')
@login_required
def manage():
    """Manage subscription."""
    if not current_user.is_premium():
        flash('You do not have an active subscription.', 'info')
        return redirect(url_for('paypal.pricing'))
    
    subscription_details = None
    if current_user.paypal_subscription_id:
        subscription_details = paypal_service.get_subscription_details(current_user.paypal_subscription_id)
    
    plans = paypal_service.get_all_plans()
    
    return render_template('paypal/manage.html',
                         subscription_details=subscription_details,
                         plans=plans)

@paypal_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel current subscription."""
    if not current_user.is_premium():
        flash('You do not have an active subscription.', 'info')
        return redirect(url_for('paypal.manage'))
    
    # Cancel in PayPal
    if current_user.paypal_subscription_id:
        success = paypal_service.cancel_subscription(current_user.paypal_subscription_id)
        if not success:
            flash('Unable to cancel subscription with PayPal. Please contact support.', 'error')
            return redirect(url_for('paypal.manage'))
    
    # Cancel locally
    if current_user.cancel_subscription():
        flash('Your subscription has been cancelled. You will continue to have access until the end of your billing period.', 'info')
    else:
        flash('Unable to cancel subscription. Please contact support.', 'error')
    
    return redirect(url_for('main.dashboard'))

@paypal_bp.route('/upgrade/<tier>')
@login_required
def upgrade(tier):
    """Upgrade subscription tier."""
    if not current_user.is_premium():
        flash('You need an active subscription to upgrade.', 'info')
        return redirect(url_for('paypal.pricing'))
    
    if tier not in ['premium', 'pro']:
        flash('Invalid subscription tier.', 'error')
        return redirect(url_for('paypal.manage'))
    
    if current_user.subscription_tier == tier:
        flash('You already have this subscription tier.', 'info')
        return redirect(url_for('paypal.manage'))
    
    # Cancel current subscription and create new one
    if current_user.paypal_subscription_id:
        paypal_service.cancel_subscription(current_user.paypal_subscription_id)
    
    # Start new subscription process
    return redirect(url_for('paypal.subscribe', tier=tier))

@paypal_bp.route('/start-trial/<tier>')
@login_required
def start_trial(tier):
    """Start a free trial."""
    if not current_user.can_start_trial():
        flash('You are not eligible for a free trial.', 'info')
        return redirect(url_for('paypal.pricing'))
    
    if tier not in ['premium', 'pro']:
        flash('Invalid trial tier.', 'error')
        return redirect(url_for('paypal.pricing'))
    
    if current_user.start_trial(tier):
        flash(f'🎉 Your {tier.title()} trial has started! You have 14 days to explore all premium features.', 'success')
        return redirect(url_for('main.dashboard'))
    else:
        flash('Unable to start trial. Please contact support.', 'error')
        return redirect(url_for('paypal.pricing'))

@paypal_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle PayPal webhooks."""
    try:
        # Verify webhook
        if not paypal_service.verify_webhook(request.headers, request.data):
            return jsonify({'error': 'Invalid webhook'}), 401
        
        # Process webhook event
        event = request.get_json()
        event_type = event.get('event_type')
        
        if event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
            # Subscription activated
            subscription_id = event.get('resource', {}).get('id')
            user = User.query.filter_by(paypal_subscription_id=subscription_id).first()
            if user:
                user.subscription_status = 'active'
                db.session.commit()
        
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            # Subscription cancelled
            subscription_id = event.get('resource', {}).get('id')
            user = User.query.filter_by(paypal_subscription_id=subscription_id).first()
            if user:
                user.subscription_status = 'cancelled'
                db.session.commit()
        
        elif event_type == 'BILLING.SUBSCRIPTION.SUSPENDED':
            # Subscription suspended
            subscription_id = event.get('resource', {}).get('id')
            user = User.query.filter_by(paypal_subscription_id=subscription_id).first()
            if user:
                user.subscription_status = 'suspended'
                db.session.commit()
        
        elif event_type == 'PAYMENT.SALE.COMPLETED':
            # Payment completed
            # Handle one-time payments if needed
            pass
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logging.error(f"PayPal webhook error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@paypal_bp.route('/api/plans')
def api_plans():
    """API endpoint to get subscription plans."""
    if not paypal_service.is_configured():
        return jsonify({'error': 'Payment system not configured'}), 503
    
    return jsonify(paypal_service.get_all_plans())

@paypal_bp.route('/api/user-subscription')
@login_required
def api_user_subscription():
    """API endpoint to get user subscription info."""
    return jsonify({
        'tier': current_user.subscription_tier,
        'status': current_user.subscription_status,
        'is_premium': current_user.is_premium(),
        'is_pro': current_user.is_pro(),
        'is_trial_active': current_user.is_trial_active(),
        'can_start_trial': current_user.can_start_trial(),
        'features': current_user.get_subscription_features(),
        'subscription_ends_at': current_user.subscription_ends_at.isoformat() if current_user.subscription_ends_at else None,
        'next_billing_date': current_user.next_billing_date.isoformat() if current_user.next_billing_date else None
    })
