from datetime import datetime
from app import db

class EntryTemplate(db.Model):
    __tablename__ = 'entry_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    category = db.Column(db.String(50), nullable=False)
    template_content = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), default='bi-journal-text')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key to users table (null for system templates)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def __repr__(self):
        return f'<EntryTemplate {self.name}>'

    @staticmethod
    def get_default_templates():
        """Get system default templates."""
        return [
            {
                'name': 'Gratitude Journal',
                'description': 'Reflect on things you are grateful for today',
                'category': 'Reflection',
                'icon': 'bi-heart',
                'template_content': '''# What I'm Grateful For Today

## Three Good Things
1. **First thing:** What made you smile or feel grateful today?
2. **Second thing:** A person, experience, or moment you appreciated?
3. **Third thing:** Something simple that brought you joy?

## Deeper Reflection
*What made these moments special? How did they make you feel?*

## Tomorrow's Intention
*How can you cultivate more gratitude in your day tomorrow?*'''
            },
            {
                'name': 'Daily Reflection',
                'description': 'Reflect on your day and lessons learned',
                'category': 'Reflection',
                'icon': 'bi-lightbulb',
                'template_content': '''# Daily Reflection

## How was your day overall?
*Rate your day from 1-10 and explain why*

## What went well today?
*List the highlights and successes*

## What challenged you?
*What difficulties did you face and how did you handle them?*

## What did you learn?
*Key insights or lessons from today*

## Tomorrow's focus
*What do you want to improve or focus on tomorrow?*'''
            },
            {
                'name': 'Goal Setting',
                'description': 'Set and track your goals and progress',
                'category': 'Goals',
                'icon': 'bi-bullseye',
                'template_content': '''# Goal Setting & Progress

## My Goals
*What are you working towards?*

### Short-term Goals (Next 1-4 weeks)
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

### Long-term Goals (1-12 months)
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## Today's Progress
*What steps did you take towards your goals today?*

## Challenges & Solutions
*What obstacles did you face and how can you overcome them?*

## Wins & Celebrations
*What progress are you proud of?*'''
            },
            {
                'name': 'Mood & Emotion Check-in',
                'description': 'Track your emotions and mental state',
                'category': 'Wellness',
                'icon': 'bi-emoji-smile',
                'template_content': '''# Mood & Emotion Check-in

## Current Mood
*How are you feeling right now? (Rate 1-10)*

## Today's Emotions
*What emotions did you experience today?*
- **Primary emotion:**
- **Secondary emotions:**

## Triggers & Patterns
*What situations or events influenced your emotions today?*

## Coping Strategies
*What helped you manage difficult emotions?*

## Self-Care Actions
*What did you do (or could you do) to support your emotional well-being?*'''
            },
            {
                'name': 'Creative Writing',
                'description': 'Free-form creative expression and ideas',
                'category': 'Creative',
                'icon': 'bi-brush',
                'template_content': '''# Creative Writing

## Writing Prompt
*Choose a prompt or write freely:*

**Prompt Ideas:**
- If you could have any superpower for a day, what would it be and why?
- Write about a place that makes you feel peaceful
- Describe your perfect day from start to finish
- Write a letter to your future self

## Your Story
*Let your imagination flow...*

## Reflections
*What inspired this piece? How does it make you feel?*'''
            },
            {
                'name': 'Learning & Growth',
                'description': 'Track new knowledge and personal development',
                'category': 'Growth',
                'icon': 'bi-book',
                'template_content': '''# Learning & Growth Journal

## What I Learned Today
*New information, skills, or insights gained*

### Key Takeaways
- **Lesson 1:**
- **Lesson 2:**
- **Lesson 3:**

## How I Applied My Learning
*Did you put any new knowledge into practice today?*

## Questions & Curiosities
*What sparked your interest? What do you want to learn more about?*

## Growth Mindset
*How did you embrace challenges or step outside your comfort zone?*'''
            },
            {
                'name': 'Dream Journal',
                'description': 'Record and analyze your dreams',
                'category': 'Wellness',
                'icon': 'bi-moon-stars',
                'template_content': '''# Dream Journal

## Dream Overview
*Brief description of what you remember*

## Key Elements
- **Setting:** Where did the dream take place?
- **People:** Who appeared in your dream?
- **Actions:** What was happening?
- **Emotions:** How did you feel during the dream?

## Symbols & Meanings
*What stood out to you? Any recurring themes or symbols?*

## Real-Life Connections
*Does this dream relate to something happening in your life?*

## Reflections
*What do you think this dream might be telling you?*'''
            },
            {
                'name': 'Quick Notes',
                'description': 'Fast capture of thoughts and ideas',
                'category': 'Quick',
                'icon': 'bi-lightning',
                'template_content': '''# Quick Notes

## Key Points
- Note 1
- Note 2
- Note 3

## Ideas & Inspiration
*Any creative thoughts or inspiration?*

## Reminders
*Things to remember or follow up on*

## Quick Reflection
*How are you feeling about these notes?*'''
            }
        ]
