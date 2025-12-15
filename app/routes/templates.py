"""
Templates and Writing Prompts Routes for My Diary App
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app.services.templates import template_service, prompt_service, collection_service
from app.models.templates import JournalTemplate, WritingPrompt, PromptCollection, TemplateRating, PromptRating, PromptResponse
from app.models.user import User
from app import db
import logging
from sqlalchemy import func, desc, or_

logger = logging.getLogger(__name__)

templates_bp = Blueprint('templates', __name__, url_prefix='/templates')


# Journal Templates Routes
@templates_bp.route('/')
@login_required
def templates_index():
    """Templates index page"""
    try:
        category = request.args.get('category', 'all')
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        page = request.args.get('page', 1, type=int)
        
        templates, total = template_service.get_templates(
            user_id=current_user.id,
            category=category,
            sort_by=sort_by,
            order=order,
            page=page
        )
        
        # Get categories
        categories = db.session.query(JournalTemplate.category, func.count(JournalTemplate.id)).group_by(JournalTemplate.category).all()
        
        # Get user's favorite templates
        favorites = template_service.get_user_favorite_templates(current_user.id, limit=5)
        
        return render_template('templates/index.html',
                             templates=templates,
                             total=total,
                             categories=categories,
                             favorites=favorites,
                             current_category=category,
                             current_sort=sort_by,
                             current_order=order)
        
    except Exception as e:
        logger.error(f"Templates index error: {str(e)}", exc_info=True)
        flash('Unable to load templates.', 'error')
        return redirect(url_for('main.dashboard'))


@templates_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create new template"""
    if request.method == 'GET':
        return render_template('templates/create.html')
    
    try:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'general')
        tags = request.form.getlist('tags')
        is_public = request.form.get('is_public') == 'on'
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('templates/create.html')
        
        template = template_service.create_template(
            user_id=current_user.id,
            title=title,
            content=content,
            description=description,
            category=category,
            tags=tags,
            is_public=is_public
        )
        
        if template:
            flash('Template created successfully!', 'success')
            return redirect(url_for('templates.view_template', template_id=template.id))
        else:
            flash('Failed to create template.', 'error')
            return render_template('templates/create.html')
        
    except Exception as e:
        logger.error(f"Create template error: {str(e)}", exc_info=True)
        flash('Failed to create template.', 'error')
        return render_template('templates/create.html')


@templates_bp.route('/<int:template_id>')
@login_required
def view_template(template_id):
    """View template details"""
    try:
        template = template_service.get_template(template_id, current_user.id)
        
        if not template:
            flash('Template not found.', 'error')
            return redirect(url_for('templates.templates_index'))
        
        # Get user's rating if exists
        user_rating = None
        if template.template_ratings:
            user_rating = next((r for r in template.template_ratings if r.user_id == current_user.id), None)
        
        return render_template('templates/view.html',
                             template=template,
                             user_rating=user_rating)
        
    except Exception as e:
        logger.error(f"View template error: {str(e)}", exc_info=True)
        flash('Template not found.', 'error')
        return redirect(url_for('templates.templates_index'))


@templates_bp.route('/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """Edit template"""
    template = template_service.get_template(template_id, current_user.id)
    
    if not template or template.created_by != current_user.id:
        flash('Template not found or access denied.', 'error')
        return redirect(url_for('templates.templates_index'))
    
    if request.method == 'GET':
        return render_template('templates/edit.html', template=template)
    
    try:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'general')
        tags = request.form.getlist('tags')
        is_public = request.form.get('is_public') == 'on'
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('templates/edit.html', template=template)
        
        updated_template = template_service.update_template(
            template_id=template_id,
            user_id=current_user.id,
            title=title,
            content=content,
            description=description,
            category=category,
            tags=tags,
            is_public=is_public
        )
        
        if updated_template:
            flash('Template updated successfully!', 'success')
            return redirect(url_for('templates.view_template', template_id=template_id))
        else:
            flash('Failed to update template.', 'error')
            return render_template('templates/edit.html', template=template)
        
    except Exception as e:
        logger.error(f"Edit template error: {str(e)}", exc_info=True)
        flash('Failed to update template.', 'error')
        return render_template('templates/edit.html', template=template)


@templates_bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete template"""
    try:
        success = template_service.delete_template(template_id, current_user.id)
        
        if success:
            flash('Template deleted successfully!', 'success')
        else:
            flash('Failed to delete template or access denied.', 'error')
        
        return redirect(url_for('templates.templates_index'))
        
    except Exception as e:
        logger.error(f"Delete template error: {str(e)}", exc_info=True)
        flash('Failed to delete template.', 'error')
        return redirect(url_for('templates.templates_index'))


@templates_bp.route('/<int:template_id>/use', methods=['POST'])
@login_required
def use_template(template_id):
    """Use template for new entry"""
    try:
        template = template_service.get_template(template_id, current_user.id)
        
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404
        
        # Track usage
        template_service.use_template(template_id, current_user.id)
        
        # Store template content in session for new entry page
        session['template_content'] = template.content
        session['template_id'] = template_id
        
        return jsonify({
            'success': True,
            'message': 'Template loaded successfully',
            'redirect_url': url_for('main.create_entry')
        })
        
    except Exception as e:
        logger.error(f"Use template error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to use template'}), 500


@templates_bp.route('/<int:template_id>/rate', methods=['POST'])
@login_required
def rate_template(template_id):
    """Rate template"""
    try:
        rating = request.form.get('rating', type=int)
        review = request.form.get('review', '').strip()
        
        if not rating or rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Invalid rating'}), 400
        
        success = template_service.rate_template(template_id, current_user.id, rating, review)
        
        if success:
            template = template_service.get_template(template_id, current_user.id)
            return jsonify({
                'success': True,
                'message': 'Rating submitted successfully',
                'new_rating': template.rating,
                'rating_count': template.rating_count
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to submit rating'}), 500
        
    except Exception as e:
        logger.error(f"Rate template error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to submit rating'}), 500


# Writing Prompts Routes
@templates_bp.route('/prompts')
@login_required
def prompts_index():
    """Writing prompts index page"""
    try:
        category = request.args.get('category', 'all')
        difficulty = request.args.get('difficulty', 'all')
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        page = request.args.get('page', 1, type=int)
        
        prompts, total = prompt_service.get_prompts(
            user_id=current_user.id,
            category=category,
            difficulty=difficulty,
            sort_by=sort_by,
            order=order,
            page=page
        )
        
        # Get daily prompt
        daily_prompt = prompt_service.get_daily_prompt()
        
        # Get categories
        categories = db.session.query(WritingPrompt.category, func.count(WritingPrompt.id)).group_by(WritingPrompt.category).all()
        
        return render_template('templates/prompts.html',
                             prompts=prompts,
                             total=total,
                             daily_prompt=daily_prompt,
                             categories=categories,
                             current_category=category,
                             current_difficulty=difficulty,
                             current_sort=sort_by,
                             current_order=order)
        
    except Exception as e:
        logger.error(f"Prompts index error: {str(e)}", exc_info=True)
        flash('Unable to load prompts.', 'error')
        return redirect(url_for('main.dashboard'))


@templates_bp.route('/prompts/daily')
@login_required
def daily_prompt():
    """Daily prompt page"""
    try:
        daily_prompt = prompt_service.get_daily_prompt()
        
        if not daily_prompt:
            flash('No daily prompt available.', 'warning')
            return redirect(url_for('templates.prompts_index'))
        
        # Get user's response history for this prompt
        user_responses = prompt_service.get_user_prompt_history(current_user.id, limit=10)
        
        return render_template('templates/daily_prompt.html',
                             daily_prompt=daily_prompt,
                             user_responses=user_responses)
        
    except Exception as e:
        logger.error(f"Daily prompt error: {str(e)}", exc_info=True)
        flash('Unable to load daily prompt.', 'error')
        return redirect(url_for('templates.prompts_index'))


@templates_bp.route('/prompts/<int:prompt_id>')
@login_required
def view_prompt(prompt_id):
    """View prompt details"""
    try:
        prompt = WritingPrompt.query.get_or_404(prompt_id)
        
        # Check access permissions
        if prompt.created_by != current_user.id and not prompt.is_public:
            flash('Prompt not found.', 'error')
            return redirect(url_for('templates.prompts_index'))
        
        # Get user's rating if exists
        user_rating = None
        if prompt.prompt_ratings:
            user_rating = next((r for r in prompt.prompt_ratings if r.user_id == current_user.id), None)
        
        # Get user's previous responses
        user_responses = PromptResponse.query.filter_by(
            prompt_id=prompt_id, user_id=current_user.id
        ).order_by(desc(PromptResponse.completed_at)).limit(5).all()
        
        return render_template('templates/view_prompt.html',
                             prompt=prompt,
                             user_rating=user_rating,
                             user_responses=user_responses)
        
    except Exception as e:
        logger.error(f"View prompt error: {str(e)}", exc_info=True)
        flash('Prompt not found.', 'error')
        return redirect(url_for('templates.prompts_index'))


# DUPLICATE REMOVED - rate_prompt function already defined at line 356


# DUPLICATE REMOVED - random_prompts function already defined at line 359


# Collections Routes
# DUPLICATE REMOVED - collections_index function already defined at line 363


# DUPLICATE REMOVED - create_collection function already defined at line 366


# DUPLICATE REMOVED - view_collection function already defined at line 369


# DUPLICATE REMOVED - add_prompt_to_collection function already defined at line 372


# API Routes for AJAX
# DUPLICATE REMOVED - recommended_templates function already defined at line 376


@templates_bp.route('/api/search')
@login_required
def search_templates():
    """Search templates and prompts"""
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')  # templates, prompts, all
        
        if not query:
            return jsonify({'success': False, 'message': 'Search query is required'}), 400
        
        results = {'templates': [], 'prompts': []}
        
        if search_type in ['templates', 'all']:
            templates = JournalTemplate.query.filter(
                or_(
                    JournalTemplate.title.ilike(f'%{query}%'),
                    JournalTemplate.description.ilike(f'%{query}%'),
                    JournalTemplate.content.ilike(f'%{query}%')
                ),
                or_(
                    JournalTemplate.created_by == current_user.id,
                    JournalTemplate.is_public == True
                )
            ).limit(10).all()
            
            results['templates'] = [template.to_dict(include_content=False) for template in templates]
        
        if search_type in ['prompts', 'all']:
            prompts = WritingPrompt.query.filter(
                or_(
                    WritingPrompt.title.ilike(f'%{query}%'),
                    WritingPrompt.prompt_text.ilike(f'%{query}%')
                ),
                or_(
                    WritingPrompt.created_by == current_user.id,
                    WritingPrompt.is_public == True
                )
            ).limit(10).all()
            
            results['prompts'] = [prompt.to_dict() for prompt in prompts]
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Search templates error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Search failed'}), 500





@templates_bp.route('/prompts/<int:prompt_id>/respond', methods=['POST'])

@login_required

def respond_to_prompt(prompt_id):

    """Respond to a writing prompt"""

    try:

        response_text = request.form.get('response_text', '').strip()

        time_spent = request.form.get('time_spent', type=int)

        create_entry = request.form.get('create_entry') == 'on'

        

        if not response_text:

            return jsonify({'success': False, 'message': 'Response cannot be empty'}), 400

        

        # Create response

        response = prompt_service.respond_to_prompt(

            prompt_id=prompt_id,

            user_id=current_user.id,

            response_text=response_text,

            time_spent=time_spent

        )

        

        if not response:

            return jsonify({'success': False, 'message': 'Failed to save response'}), 500

        

        result = {

            'success': True,

            'message': 'Response saved successfully',

            'response_id': response.id

        }

        

        # Create entry if requested

        if create_entry:

            prompt = WritingPrompt.query.get(prompt_id)

            entry_content = f"Prompt: {prompt.title}\n\n{prompt.prompt_text}\n\nResponse:\n{response_text}"

            

            # Store in session for new entry creation

            session['prompt_response_content'] = entry_content

            session['prompt_id'] = prompt_id

            

            result['create_entry_url'] = url_for('main.create_entry')

        

        return jsonify(result)

        

    except Exception as e:

        logger.error(f"Respond to prompt error: {str(e)}", exc_info=True)

        return jsonify({'success': False, 'message': 'Failed to save response'}), 500





@templates_bp.route('/prompts/<int:prompt_id>/rate', methods=['POST'])

@login_required

def rate_prompt(prompt_id):

    """Rate prompt"""

    try:

        rating = request.form.get('rating', type=int)

        review = request.form.get('review', '').strip()

        

        if not rating or rating < 1 or rating > 5:

            return jsonify({'success': False, 'message': 'Invalid rating'}), 400

        

        prompt = WritingPrompt.query.get_or_404(prompt_id)

        

        # Check access permissions

        if prompt.created_by != current_user.id and not prompt.is_public:

            return jsonify({'success': False, 'message': 'Prompt not found'}), 404

        

        # Check if user already rated

        existing_rating = PromptRating.query.filter_by(

            prompt_id=prompt_id, user_id=current_user.id

        ).first()

        

        if existing_rating:

            existing_rating.rating = rating

            existing_rating.review = review

            existing_rating.created_at = datetime.utcnow()

        else:

            new_rating = PromptRating(

                prompt_id=prompt_id,

                user_id=current_user.id,

                rating=rating,

                review=review

            )

            db.session.add(new_rating)

        

        # Update prompt rating

        prompt.update_rating()

        db.session.commit()

        

        return jsonify({

            'success': True,

            'message': 'Rating submitted successfully',

            'new_rating': prompt.rating,

            'rating_count': prompt.rating_count

        })

        

    except Exception as e:

        logger.error(f"Rate prompt error: {str(e)}", exc_info=True)

        return jsonify({'success': False, 'message': 'Failed to submit rating'}), 500





@templates_bp.route('/prompts/random')

@login_required

def random_prompts():

    """Get random prompts"""

    try:

        count = request.args.get('count', 5, type=int)

        category = request.args.get('category', 'all')

        difficulty = request.args.get('difficulty', 'all')

        

        prompts = prompt_service.get_random_prompts(

            count=count,

            category=category,

            difficulty=difficulty,

            user_id=current_user.id

        )

        

        return jsonify({

            'success': True,

            'prompts': [prompt.to_dict() for prompt in prompts]

        })

        

    except Exception as e:

        logger.error(f"Random prompts error: {str(e)}", exc_info=True)

        return jsonify({'success': False, 'message': 'Failed to get random prompts'}), 500





# Collections Routes

@templates_bp.route('/collections')

@login_required

def collections_index():

    """Prompt collections index page"""

    try:

        collections = collection_service.get_collections(current_user.id)

        

        return render_template('templates/collections.html', collections=collections)

        

    except Exception as e:

        logger.error(f"Collections index error: {str(e)}", exc_info=True)

        flash('Unable to load collections.', 'error')

        return redirect(url_for('main.dashboard'))





@templates_bp.route('/collections/create', methods=['GET', 'POST'])

@login_required

def create_collection():

    """Create new collection"""

    if request.method == 'GET':

        return render_template('templates/create_collection.html')

    

    try:

        name = request.form.get('name', '').strip()

        description = request.form.get('description', '').strip()

        category = request.form.get('category', 'general')

        is_public = request.form.get('is_public') == 'on'

        

        if not name:

            flash('Collection name is required.', 'error')

            return render_template('templates/create_collection.html')

        

        collection = collection_service.create_collection(

            user_id=current_user.id,

            name=name,

            description=description,

            category=category,

            is_public=is_public

        )

        

        if collection:

            flash('Collection created successfully!', 'success')

            return redirect(url_for('templates.view_collection', collection_id=collection.id))

        else:

            flash('Failed to create collection.', 'error')

            return render_template('templates/create_collection.html')

        

    except Exception as e:

        logger.error(f"Create collection error: {str(e)}", exc_info=True)

        flash('Failed to create collection.', 'error')

        return render_template('templates/create_collection.html')





@templates_bp.route('/collections/<int:collection_id>')

@login_required

def view_collection(collection_id):

    """View collection details"""

    try:

        collection = PromptCollection.query.get_or_404(collection_id)

        

        # Check access permissions

        if collection.created_by != current_user.id and not collection.is_public:

            flash('Collection not found.', 'error')

            return redirect(url_for('templates.collections_index'))

        

        return render_template('templates/view_collection.html',

                             collection=collection.to_dict(include_prompts=True))

        

    except Exception as e:

        logger.error(f"View collection error: {str(e)}", exc_info=True)

        flash('Collection not found.', 'error')

        return redirect(url_for('templates.collections_index'))





@templates_bp.route('/collections/<int:collection_id>/add-prompt', methods=['POST'])

@login_required

def add_prompt_to_collection(collection_id):

    """Add prompt to collection"""

    try:

        prompt_id = request.form.get('prompt_id', type=int)

        

        if not prompt_id:

            return jsonify({'success': False, 'message': 'Prompt ID is required'}), 400

        

        success = collection_service.add_prompt_to_collection(

            collection_id=collection_id,

            prompt_id=prompt_id,

            user_id=current_user.id

        )

        

        if success:

            return jsonify({

                'success': True,

                'message': 'Prompt added to collection successfully'

            })

        else:

            return jsonify({'success': False, 'message': 'Failed to add prompt to collection'}), 500

        

    except Exception as e:

        logger.error(f"Add prompt to collection error: {str(e)}", exc_info=True)

        return jsonify({'success': False, 'message': 'Failed to add prompt to collection'}), 500





# API Routes for AJAX

@templates_bp.route('/api/recommended')

@login_required

def recommended_templates():

    """Get recommended templates for user"""

    try:

        templates = template_service.get_recommended_templates(current_user.id, limit=5)

        

        return jsonify({

            'success': True,

            'templates': [template.to_dict(include_content=False) for template in templates]

        })

        

    except Exception as e:

        logger.error(f"Recommended templates error: {str(e)}", exc_info=True)

        return jsonify({'success': False, 'message': 'Failed to get recommendations'}), 500






