"""
Templates and Writing Prompts Services for My Diary App
"""

import json
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, desc, asc, or_, and_
from app.models.templates import (
    JournalTemplate, WritingPrompt, TemplateRating, PromptRating,
    TemplateUsage, PromptResponse, DailyPrompt, PromptCollection,
    CollectionItem, UserTemplatePreference, UserPromptPreference
)
from app.models.user import User
from app.models.entry import Entry
from app import db
import logging

logger = logging.getLogger(__name__)


class TemplateService:
    """Journal template service"""
    
    @staticmethod
    def get_templates(user_id: Optional[int] = None, category: str = None, 
                     is_public: bool = True, include_premium: bool = False,
                     sort_by: str = 'created_at', order: str = 'desc',
                     page: int = 1, per_page: int = 20) -> Tuple[List[JournalTemplate], int]:
        """Get templates with filters and pagination"""
        try:
            query = JournalTemplate.query
            
            # Filter by user or public
            if user_id:
                query = query.filter(or_(
                    JournalTemplate.created_by == user_id,
                    JournalTemplate.is_public == True
                ))
            else:
                query = query.filter(JournalTemplate.is_public == True)
            
            # Filter by category
            if category and category != 'all':
                query = query.filter(JournalTemplate.category == category)
            
            # Filter premium templates
            if not include_premium:
                query = query.filter(JournalTemplate.is_premium == False)
            
            # Sort
            if sort_by == 'rating':
                query = query.order_by(desc(JournalTemplate.rating), desc(JournalTemplate.usage_count))
            elif sort_by == 'usage':
                query = query.order_by(desc(JournalTemplate.usage_count))
            elif sort_by == 'title':
                query = query.order_by(asc(JournalTemplate.title))
            else:  # created_at
                if order == 'asc':
                    query = query.order_by(asc(JournalTemplate.created_at))
                else:
                    query = query.order_by(desc(JournalTemplate.created_at))
            
            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return pagination.items, pagination.total
            
        except Exception as e:
            logger.error(f"Get templates error: {str(e)}")
            return [], 0
    
    @staticmethod
    def get_template(template_id: int, user_id: Optional[int] = None) -> Optional[JournalTemplate]:
        """Get single template"""
        try:
            template = JournalTemplate.query.get(template_id)
            
            if not template:
                return None
            
            # Check access permissions
            if user_id:
                if template.created_by != user_id and not template.is_public:
                    return None
            else:
                if not template.is_public:
                    return None
            
            return template
            
        except Exception as e:
            logger.error(f"Get template error: {str(e)}")
            return None
    
    @staticmethod
    def create_template(user_id: int, title: str, content: str, description: str = '',
                       category: str = 'general', tags: List[str] = None,
                       is_public: bool = False, is_premium: bool = False) -> Optional[JournalTemplate]:
        """Create new template"""
        try:
            template = JournalTemplate(
                title=title,
                content=content,
                description=description,
                category=category,
                is_public=is_public,
                is_premium=is_premium,
                created_by=user_id
            )
            
            template.set_tags_list(tags or [])
            
            db.session.add(template)
            db.session.commit()
            
            logger.info(f"Template created: {template.id} by user {user_id}")
            return template
            
        except Exception as e:
            logger.error(f"Create template error: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_template(template_id: int, user_id: int, **kwargs) -> Optional[JournalTemplate]:
        """Update template"""
        try:
            template = JournalTemplate.query.filter_by(id=template_id, created_by=user_id).first()
            
            if not template:
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(template, key):
                    if key == 'tags' and isinstance(value, list):
                        template.set_tags_list(value)
                    else:
                        setattr(template, key, value)
            
            template.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Template updated: {template_id} by user {user_id}")
            return template
            
        except Exception as e:
            logger.error(f"Update template error: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def delete_template(template_id: int, user_id: int) -> bool:
        """Delete template"""
        try:
            template = JournalTemplate.query.filter_by(id=template_id, created_by=user_id).first()
            
            if not template:
                return False
            
            db.session.delete(template)
            db.session.commit()
            
            logger.info(f"Template deleted: {template_id} by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Delete template error: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def rate_template(template_id: int, user_id: int, rating: int, review: str = '') -> bool:
        """Rate template"""
        try:
            # Check if user already rated
            existing_rating = TemplateRating.query.filter_by(
                template_id=template_id, user_id=user_id
            ).first()
            
            if existing_rating:
                existing_rating.rating = rating
                existing_rating.review = review
                existing_rating.created_at = datetime.utcnow()
            else:
                new_rating = TemplateRating(
                    template_id=template_id,
                    user_id=user_id,
                    rating=rating,
                    review=review
                )
                db.session.add(new_rating)
            
            # Update template rating
            template = JournalTemplate.query.get(template_id)
            if template:
                template.update_rating()
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Rate template error: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def use_template(template_id: int, user_id: int, entry_id: Optional[int] = None) -> bool:
        """Track template usage"""
        try:
            # Record usage
            usage = TemplateUsage(
                template_id=template_id,
                user_id=user_id,
                entry_id=entry_id
            )
            db.session.add(usage)
            
            # Update template usage count
            template = JournalTemplate.query.get(template_id)
            if template:
                template.increment_usage()
            
            # Update user preference
            preference = UserTemplatePreference.query.filter_by(
                template_id=template_id, user_id=user_id
            ).first()
            
            if preference:
                preference.usage_frequency += 1
                preference.last_used = datetime.utcnow()
            else:
                preference = UserTemplatePreference(
                    template_id=template_id,
                    user_id=user_id,
                    usage_frequency=1,
                    last_used=datetime.utcnow()
                )
                db.session.add(preference)
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Use template error: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_user_favorite_templates(user_id: int, limit: int = 10) -> List[JournalTemplate]:
        """Get user's favorite templates"""
        try:
            return db.session.query(JournalTemplate).join(
                UserTemplatePreference, JournalTemplate.id == UserTemplatePreference.template_id
            ).filter(
                UserTemplatePreference.user_id == user_id,
                UserTemplatePreference.is_favorite == True
            ).order_by(desc(UserTemplatePreference.last_used)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Get favorite templates error: {str(e)}")
            return []
    
    @staticmethod
    def get_recommended_templates(user_id: int, limit: int = 5) -> List[JournalTemplate]:
        """Get recommended templates for user"""
        try:
            # Get user's most used categories
            user_categories = db.session.query(
                JournalTemplate.category,
                func.count(TemplateUsage.id).label('usage_count')
            ).join(TemplateUsage).filter(
                TemplateUsage.user_id == user_id
            ).group_by(JournalTemplate.category).order_by(
                desc('usage_count')
            ).limit(3).all()
            
            category_list = [cat.category for cat in user_categories]
            
            # Get templates from user's preferred categories
            recommended = JournalTemplate.query.filter(
                JournalTemplate.is_public == True,
                JournalTemplate.category.in_(category_list) if category_list else True
            ).order_by(desc(JournalTemplate.rating)).limit(limit).all()
            
            # If not enough, add popular templates
            if len(recommended) < limit:
                popular = JournalTemplate.query.filter(
                    JournalTemplate.is_public == True,
                    ~JournalTemplate.id.in_([t.id for t in recommended])
                ).order_by(desc(JournalTemplate.usage_count)).limit(
                    limit - len(recommended)
                ).all()
                recommended.extend(popular)
            
            return recommended[:limit]
            
        except Exception as e:
            logger.error(f"Get recommended templates error: {str(e)}")
            return []


class PromptService:
    """Writing prompt service"""
    
    @staticmethod
    def get_prompts(user_id: Optional[int] = None, category: str = None,
                   difficulty: str = None, is_public: bool = True,
                   include_premium: bool = False, sort_by: str = 'created_at',
                   order: str = 'desc', page: int = 1, per_page: int = 20) -> Tuple[List[WritingPrompt], int]:
        """Get prompts with filters and pagination"""
        try:
            query = WritingPrompt.query
            
            # Filter by user or public
            if user_id:
                query = query.filter(or_(
                    WritingPrompt.created_by == user_id,
                    WritingPrompt.is_public == True
                ))
            else:
                query = query.filter(WritingPrompt.is_public == True)
            
            # Filter by category
            if category and category != 'all':
                query = query.filter(WritingPrompt.category == category)
            
            # Filter by difficulty
            if difficulty and difficulty != 'all':
                query = query.filter(WritingPrompt.difficulty == difficulty)
            
            # Filter premium prompts
            if not include_premium:
                query = query.filter(WritingPrompt.is_premium == False)
            
            # Sort
            if sort_by == 'rating':
                query = query.order_by(desc(WritingPrompt.rating), desc(WritingPrompt.usage_count))
            elif sort_by == 'usage':
                query = query.order_by(desc(WritingPrompt.usage_count))
            elif sort_by == 'difficulty':
                query = query.order_by(asc(WritingPrompt.difficulty))
            else:  # created_at
                if order == 'asc':
                    query = query.order_by(asc(WritingPrompt.created_at))
                else:
                    query = query.order_by(desc(WritingPrompt.created_at))
            
            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return pagination.items, pagination.total
            
        except Exception as e:
            logger.error(f"Get prompts error: {str(e)}")
            return [], 0
    
    @staticmethod
    def get_daily_prompt(target_date: Optional[date] = None) -> Optional[WritingPrompt]:
        """Get daily prompt for specific date"""
        try:
            target_date = target_date or date.today()
            
            # Try to get existing daily prompt
            daily_prompt = DailyPrompt.query.filter_by(date=target_date, is_active=True).first()
            
            if daily_prompt:
                return daily_prompt.prompt
            
            # If no daily prompt exists, create one
            # Get a random public prompt
            prompt = WritingPrompt.query.filter(
                WritingPrompt.is_public == True
            ).order_by(func.random()).first()
            
            if prompt:
                # Create daily prompt record
                daily_prompt = DailyPrompt(
                    prompt_id=prompt.id,
                    date=target_date
                )
                db.session.add(daily_prompt)
                db.session.commit()
                
                return prompt
            
            return None
            
        except Exception as e:
            logger.error(f"Get daily prompt error: {str(e)}")
            return None
    
    @staticmethod
    def get_random_prompts(count: int = 5, category: str = None,
                          difficulty: str = None, user_id: Optional[int] = None) -> List[WritingPrompt]:
        """Get random prompts"""
        try:
            query = WritingPrompt.query.filter(WritingPrompt.is_public == True)
            
            if category and category != 'all':
                query = query.filter(WritingPrompt.category == category)
            
            if difficulty and difficulty != 'all':
                query = query.filter(WritingPrompt.difficulty == difficulty)
            
            # Exclude prompts already used by user today
            if user_id:
                today_responses = db.session.query(PromptResponse.prompt_id).filter(
                    PromptResponse.user_id == user_id,
                    func.date(PromptResponse.completed_at) == date.today()
                ).subquery()
                
                query = query.filter(~WritingPrompt.id.in_(today_responses))
            
            return query.order_by(func.random()).limit(count).all()
            
        except Exception as e:
            logger.error(f"Get random prompts error: {str(e)}")
            return []
    
    @staticmethod
    def create_prompt(user_id: int, title: str, prompt_text: str,
                     category: str = 'general', difficulty: str = 'medium',
                     tags: List[str] = None, is_public: bool = True,
                     is_premium: bool = False, estimated_time: int = None,
                     word_count_goal: int = None) -> Optional[WritingPrompt]:
        """Create new writing prompt"""
        try:
            prompt = WritingPrompt(
                title=title,
                prompt_text=prompt_text,
                category=category,
                difficulty=difficulty,
                is_public=is_public,
                is_premium=is_premium,
                estimated_time=estimated_time,
                word_count_goal=word_count_goal,
                created_by=user_id
            )
            
            prompt.set_tags_list(tags or [])
            
            db.session.add(prompt)
            db.session.commit()
            
            logger.info(f"Prompt created: {prompt.id} by user {user_id}")
            return prompt
            
        except Exception as e:
            logger.error(f"Create prompt error: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def respond_to_prompt(prompt_id: int, user_id: int, response_text: str,
                         time_spent: int = None, entry_id: Optional[int] = None) -> Optional[PromptResponse]:
        """Respond to a writing prompt"""
        try:
            response = PromptResponse(
                prompt_id=prompt_id,
                user_id=user_id,
                response_text=response_text,
                word_count=len(response_text.split()),
                time_spent=time_spent,
                entry_id=entry_id
            )
            
            db.session.add(response)
            
            # Update prompt usage
            prompt = WritingPrompt.query.get(prompt_id)
            if prompt:
                prompt.increment_usage()
            
            # Update user preference
            preference = UserPromptPreference.query.filter_by(
                prompt_id=prompt_id, user_id=user_id
            ).first()
            
            if preference:
                preference.last_used = datetime.utcnow()
            else:
                preference = UserPromptPreference(
                    prompt_id=prompt_id,
                    user_id=user_id,
                    last_used=datetime.utcnow()
                )
                db.session.add(preference)
            
            db.session.commit()
            return response
            
        except Exception as e:
            logger.error(f"Respond to prompt error: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_user_prompt_history(user_id: int, limit: int = 20) -> List[PromptResponse]:
        """Get user's prompt response history"""
        try:
            return PromptResponse.query.filter_by(user_id=user_id).order_by(
                desc(PromptResponse.completed_at)
            ).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Get prompt history error: {str(e)}")
            return []
    
    @staticmethod
    def get_prompt_streak(user_id: int) -> int:
        """Get user's prompt response streak"""
        try:
            # Get consecutive days with prompt responses
            streak = 0
            current_date = date.today()
            
            while True:
                response_exists = db.session.query(PromptResponse).filter(
                    PromptResponse.user_id == user_id,
                    func.date(PromptResponse.completed_at) == current_date
                ).first()
                
                if response_exists:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"Get prompt streak error: {str(e)}")
            return 0


class CollectionService:
    """Prompt collection service"""
    
    @staticmethod
    def get_collections(user_id: Optional[int] = None, include_public: bool = True) -> List[PromptCollection]:
        """Get collections"""
        try:
            query = PromptCollection.query
            
            if user_id:
                query = query.filter(or_(
                    PromptCollection.created_by == user_id,
                    PromptCollection.is_public == True
                ))
            elif include_public:
                query = query.filter(PromptCollection.is_public == True)
            else:
                return []
            
            return query.order_by(desc(PromptCollection.usage_count)).all()
            
        except Exception as e:
            logger.error(f"Get collections error: {str(e)}")
            return []
    
    @staticmethod
    def create_collection(user_id: int, name: str, description: str = '',
                         category: str = 'general', is_public: bool = False,
                         is_premium: bool = False) -> Optional[PromptCollection]:
        """Create new collection"""
        try:
            collection = PromptCollection(
                name=name,
                description=description,
                category=category,
                is_public=is_public,
                is_premium=is_premium,
                created_by=user_id
            )
            
            db.session.add(collection)
            db.session.commit()
            
            logger.info(f"Collection created: {collection.id} by user {user_id}")
            return collection
            
        except Exception as e:
            logger.error(f"Create collection error: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def add_prompt_to_collection(collection_id: int, prompt_id: int, user_id: int) -> bool:
        """Add prompt to collection"""
        try:
            # Check if collection belongs to user or is public
            collection = PromptCollection.query.filter_by(id=collection_id).first()
            if not collection or (collection.created_by != user_id and not collection.is_public):
                return False
            
            # Check if prompt already in collection
            existing = CollectionItem.query.filter_by(
                collection_id=collection_id, prompt_id=prompt_id
            ).first()
            
            if existing:
                return False
            
            # Add prompt to collection
            item = CollectionItem(
                collection_id=collection_id,
                prompt_id=prompt_id,
                order=CollectionItem.query.filter_by(collection_id=collection_id).count()
            )
            db.session.add(item)
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Add prompt to collection error: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def remove_prompt_from_collection(collection_id: int, prompt_id: int, user_id: int) -> bool:
        """Remove prompt from collection"""
        try:
            # Check if collection belongs to user
            collection = PromptCollection.query.filter_by(id=collection_id, created_by=user_id).first()
            if not collection:
                return False
            
            # Remove prompt from collection
            item = CollectionItem.query.filter_by(
                collection_id=collection_id, prompt_id=prompt_id
            ).first()
            
            if item:
                db.session.delete(item)
                db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Remove prompt from collection error: {str(e)}")
            db.session.rollback()
            return False


# Initialize services
template_service = TemplateService()
prompt_service = PromptService()
collection_service = CollectionService()
