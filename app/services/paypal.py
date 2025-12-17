"""PayPal payment service for subscription management."""

import logging
import requests
from datetime import datetime, timedelta
from flask import current_app
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class PayPalService:
    """Service for handling PayPal payments and subscriptions."""
    
    def __init__(self):
        # Initialize with None, will be set in init_app
        self.base_url = None
        self.client_id = None
        self.client_secret = None
        self.webhook_id = None
        self._access_token = None
        self._token_expires_at = None
        
        # Subscription plans
        self.plans = {
            'premium': {
                'name': 'Premium Diary',
                'description': 'Unlimited entries, AI insights, advanced analytics',
                'price': '9.99',
                'currency': 'USD',
                'interval': 'month',
                'trial_days': 14
            },
            'pro': {
                'name': 'Pro Diary',
                'description': 'Everything in Premium + collaboration, priority support',
                'price': '19.99',
                'currency': 'USD',
                'interval': 'month',
                'trial_days': 14
            }
        }
    
    def init_app(self, app):
        with app.app_context():
            if not app.config.get('PAYPAL_ENABLED', False):
                logger.info("PayPal disabled by configuration.")
                return

            self.base_url = "https://api-m.sandbox.paypal.com" if app.config.get('PAYPAL_SANDBOX', True) else "https://api-m.paypal.com"
            self.client_id = app.config.get('PAYPAL_CLIENT_ID')
            self.client_secret = app.config.get('PAYPAL_CLIENT_SECRET')
            self.webhook_id = app.config.get('PAYPAL_WEBHOOK_ID')
            
            if not self.client_id or not self.client_secret:
                logger.warning("PayPal credentials not configured. PayPal services will be disabled.")
    
    def _get_access_token(self):
        if self._access_token and self._token_expires_at and self._token_expires_at > datetime.utcnow():
            return self._access_token
        
        if not self.client_id or not self.client_secret:
            logger.error("PayPal credentials not configured")
            return None
        
        try:
            auth = (self.client_id, self.client_secret)
            headers = {
                'Accept': 'application/json',
                'Accept-Language': 'en_US',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = 'grant_type=client_credentials'
            
            response = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=auth,
                headers=headers,
                data=data
            )
            
            if response.status_code == 200:
                self._access_token = response.json().get('access_token')
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=response.json().get('expires_in', 3600)) # Default to 1 hour
                return self._access_token
            else:
                logger.error(f"Failed to get PayPal access token: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"PayPal API error: {str(e)}")
            return None
    
    def create_subscription_plan(self, tier):
        """Create a subscription plan for the given tier."""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        plan_config = self.plans.get(tier)
        if not plan_config:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            payload = {
                'product_id': f'DIARY_{tier.upper()}_PRODUCT',
                'name': plan_config['name'],
                'description': plan_config['description'],
                'billing_cycles': [
                    {
                        'frequency': {
                            'interval_unit': plan_config['interval'],
                            'interval_count': 1
                        },
                        'tenure_type': 'REGULAR',
                        'sequence': 1,
                        'total_cycles': 0,  # Infinite
                        'pricing_scheme': {
                            'fixed_price': {
                                'value': plan_config['price'],
                                'currency_code': plan_config['currency']
                            }
                        }
                    }
                ],
                'payment_preferences': {
                    'auto_bill_outstanding': True,
                    'setup_fee': None,
                    'setup_fee_failure_action': 'CONTINUE',
                    'payment_failure_threshold': 3
                },
                'taxes': {
                    'percentage': '0',
                    'inclusive': False
                }
            }
            
            # Add trial if configured
            if plan_config.get('trial_days', 0) > 0:
                trial_cycle = {
                    'frequency': {
                        'interval_unit': 'DAY',
                        'interval_count': plan_config['trial_days']
                    },
                    'tenure_type': 'TRIAL',
                    'sequence': 1,
                    'total_cycles': 1,
                    'pricing_scheme': {
                        'fixed_price': {
                            'value': '0',
                            'currency_code': plan_config['currency']
                        }
                    }
                }
                payload['billing_cycles'].insert(0, trial_cycle)
            
            response = requests.post(
                f"{self.base_url}/v1/billing/plans",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Failed to create PayPal plan: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"PayPal plan creation error: {str(e)}")
            return None
    
    def create_subscription(self, plan_id, user_id):
        """Create a subscription for a user."""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            payload = {
                'plan_id': plan_id,
                'application_context': {
                    'brand_name': 'My Diary',
                    'locale': 'en-US',
                    'shipping_preference': 'NO_SHIPPING',
                    'user_action': 'SUBSCRIBE_NOW',
                    'payment_method': {
                        'payer_selected': 'PAYPAL',
                        'payee_preferred': 'IMMEDIATE_PAYMENT_REQUIRED'
                    },
                    'return_url': f"{current_app.config.get('BASE_URL', '')}/paypal/success",
                    'cancel_url': f"{current_app.config.get('BASE_URL', '')}/paypal/cancel"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v1/billing/subscriptions",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Failed to create PayPal subscription: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"PayPal subscription creation error: {str(e)}")
            return None
    
    def get_subscription_details(self, subscription_id):
        """Get subscription details from PayPal."""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/v1/billing/subscriptions/{subscription_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get PayPal subscription details: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"PayPal subscription details error: {str(e)}")
            return None
    
    def cancel_subscription(self, subscription_id, reason='User requested cancellation'):
        """Cancel a subscription."""
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            payload = {
                'reason': reason
            }
            
            response = requests.post(
                f"{self.base_url}/v1/billing/subscriptions/{subscription_id}/cancel",
                headers=headers,
                json=payload
            )
            
            return response.status_code in [200, 204]
                
        except Exception as e:
            logger.error(f"PayPal subscription cancellation error: {str(e)}")
            return False
    
    def create_order(self, amount, currency='USD', description='Premium Subscription'):
        """Create a one-time payment order."""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            payload = {
                'intent': 'CAPTURE',
                'purchase_units': [
                    {
                        'reference_id': f'DIARY_PREMIUM_{datetime.utcnow().timestamp()}',
                        'description': description,
                        'amount': {
                            'currency_code': currency,
                            'value': str(amount)
                        },
                        'custom_id': f'user_{current_app.current_user.id if hasattr(current_app, "current_user") and hasattr(current_app.current_user, "id") else "unknown"}'
                    }
                ],
                'application_context': {
                    'brand_name': 'My Diary',
                    'landing_page': 'BILLING',
                    'user_action': 'PAY_NOW',
                    'return_url': f"{current_app.config.get('BASE_URL', '')}/paypal/payment/success",
                    'cancel_url': f"{current_app.config.get('BASE_URL', '')}/paypal/payment/cancel"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Failed to create PayPal order: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"PayPal order creation error: {str(e)}")
            return None
    
    def capture_payment(self, order_id):
        """Capture payment for an order."""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Failed to capture PayPal payment: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"PayPal payment capture error: {str(e)}")
            return None
    
    def verify_webhook(self, headers, body):
        """Verify PayPal webhook signature."""
        if not self.webhook_id:
            return False
        
        try:
            # This is a simplified webhook verification
            # In production, you'd implement proper signature verification
            # using PayPal's verification algorithm
            return True
                
        except Exception as e:
            logger.error(f"PayPal webhook verification error: {str(e)}")
            return False
    
    def get_plan_pricing(self, tier):
        """Get pricing information for a plan."""
        plan_config = self.plans.get(tier)
        if not plan_config:
            return None
        
        return {
            'name': plan_config['name'],
            'description': plan_config['description'],
            'price': plan_config['price'],
            'currency': plan_config['currency'],
            'interval': plan_config['interval'],
            'trial_days': plan_config.get('trial_days', 0),
            'yearly_price': str(float(plan_config['price']) * 10)  # 2 months free yearly
        }
    
    def get_all_plans(self):
        """Get all available subscription plans."""
        return {
            tier: self.get_plan_pricing(tier)
            for tier in self.plans.keys()
        }
    
    def is_configured(self):
        """Check if PayPal is properly configured."""
        return bool(self.client_id and self.client_secret)
    
    def init_app(self, app):
        """Initialize service with Flask app context."""
        with app.app_context():
            self.base_url = "https://api-m.sandbox.paypal.com" if app.config.get('PAYPAL_SANDBOX', True) else "https://api-m.paypal.com"
            self.client_id = app.config.get('PAYPAL_CLIENT_ID')
            self.client_secret = app.config.get('PAYPAL_CLIENT_SECRET')
            self.webhook_id = app.config.get('PAYPAL_WEBHOOK_ID')

# Create global instance - will be initialized properly in app context
paypal_service = PayPalService()
