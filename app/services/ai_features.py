"""
AI Features Service for My Diary App

This service provides:
- Smart writing suggestions
- Mood analysis and insights
- Personalized writing prompts
- Content analysis and recommendations
"""

import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from app.models.entry import Entry


class AIFeaturesService:
    """AI-powered features for enhanced diary writing experience."""
    
    def __init__(self):
        self.writing_prompts = self._initialize_prompts()
        self.mood_insights = self._initialize_mood_insights()
        self.suggestion_templates = self._initialize_suggestions()
    
    def _initialize_prompts(self) -> Dict[str, List[str]]:
        """Initialize writing prompts by category."""
        return {
            'reflection': [
                "What was the most meaningful moment of your day?",
                "How did you grow as a person today?",
                "What are you grateful for right now?",
                "What challenge did you overcome today?",
                "What made you smile today?",
                "How did you make someone else's day better?",
                "What did you learn about yourself today?",
                "What would you do differently if you could replay today?"
            ],
            'creativity': [
                "If today was a chapter in a book, what would its title be?",
                "Describe your day using only colors and emotions.",
                "Write a letter to your future self about today.",
                "If your day had a soundtrack, what songs would be on it?",
                "Create a metaphor for how your day unfolded.",
                "Describe today from the perspective of an object you used frequently.",
                "What story would today tell if it could speak?",
                "If today was a weather pattern, what would it be and why?"
            ],
            'goal_setting': [
                "What small step can you take tomorrow toward your goals?",
                "What habit would you like to build or break?",
                "How can tomorrow be better than today?",
                "What's one thing you want to accomplish this week?",
                "What skill would you like to develop?",
                "How can you take better care of yourself tomorrow?",
                "What relationship needs more attention?",
                "What fear would you like to overcome?"
            ],
            'emotional_processing': [
                "What emotions are you carrying right now?",
                "How did you handle stress today?",
                "When did you feel most at peace today?",
                "What triggered strong emotions today?",
                "How did you express your feelings today?",
                "What would you tell your younger self about today?",
                "How did you practice self-compassion today?",
                "What emotional pattern do you notice in your writing?"
            ]
        }
    
    def _initialize_mood_insights(self) -> Dict[str, Dict]:
        """Initialize mood-based insights and recommendations."""
        return {
            '😊 Happy': {
                'insights': [
                    "You're in a great mood! This is perfect for creative writing and goal setting.",
                    "Your positive energy can help you tackle challenges and inspire others.",
                    "Use this happiness to strengthen relationships and pursue passions."
                ],
                'prompts': [
                    "What made you feel this happy today?",
                    "How can you share this joy with others?",
                    "What positive patterns led to this happiness?"
                ],
                'activities': [
                    "Write about things you're grateful for",
                    "Plan something exciting for tomorrow",
                    "Reach out to someone who makes you happy"
                ]
            },
            '😢 Sad': {
                'insights': [
                    "It's okay to feel sad. Writing can help process these emotions.",
                    "Sadness often leads to deeper self-reflection and understanding.",
                    "This emotion can be a powerful source of creative expression."
                ],
                'prompts': [
                    "What's behind this feeling?",
                    "What would comfort you right now?",
                    "What have you learned from difficult times before?"
                ],
                'activities': [
                    "Write about your feelings without judgment",
                    "List things that usually help you feel better",
                    "Plan a small act of self-care"
                ]
            },
            '😡 Angry': {
                'insights': [
                    "Anger often signals that something important needs attention.",
                    "This emotion can motivate positive change and boundary setting.",
                    "Writing can help you understand the root cause and find solutions."
                ],
                'prompts': [
                    "What triggered this anger?",
                    "What boundary needs to be set?",
                    "How can you channel this energy constructively?"
                ],
                'activities': [
                    "Write a letter you won't send",
                    "Identify the underlying need or fear",
                    "Plan a constructive action step"
                ]
            },
            '😴 Tired': {
                'insights': [
                    "Rest is essential. Your body and mind need recovery time.",
                    "Fatigue can signal burnout or the need for lifestyle changes.",
                    "This is a good time for gentle reflection and planning."
                ],
                'prompts': [
                    "What's draining your energy?",
                    "What would help you feel more rested?",
                    "How can you prioritize rest tomorrow?"
                ],
                'activities': [
                    "Write about your sleep quality",
                    "List energy-boosting activities",
                    "Plan a relaxing evening routine"
                ]
            }
        }
    
    def _initialize_suggestions(self) -> Dict[str, List[str]]:
        """Initialize smart writing suggestions."""
        return {
            'opening_lines': [
                "Today was...",
                "I'm feeling...",
                "The most important thing that happened today was...",
                "I keep thinking about...",
                "What surprised me most was...",
                "Today taught me that...",
                "I'm grateful for...",
                "Looking back, I realize..."
            ],
            'reflection_questions': [
                "How did this make me feel?",
                "What did I learn from this?",
                "Why was this moment significant?",
                "How does this connect to my goals?",
                "What would I do differently?",
                "How can I grow from this experience?",
                "What pattern am I noticing?",
                "How does this align with my values?"
            ],
            'closing_thoughts': [
                "Tomorrow, I hope to...",
                "I'm taking away...",
                "This reminds me that...",
                "I'm committed to...",
                "I'm curious about...",
                "I trust that...",
                "I celebrate...",
                "I release..."
            ]
        }
    
    def get_personalized_prompt(self, user_entries: List[Entry], current_mood: str = None) -> Dict:
        """Generate a personalized writing prompt based on user history and mood."""
        if not user_entries:
            return self._get_random_prompt()
        
        # Analyze recent patterns
        recent_entries = user_entries[-10:] if len(user_entries) > 10 else user_entries
        mood_pattern = self._analyze_mood_pattern(recent_entries)
        content_themes = self._analyze_content_themes(recent_entries)
        
        # Select prompt category based on patterns
        if current_mood and current_mood in self.mood_insights:
            prompts = self.mood_insights[current_mood]['prompts']
            prompt = random.choice(prompts)
            category = 'mood_based'
        elif mood_pattern == 'declining':
            prompts = self.writing_prompts['emotional_processing']
            prompt = random.choice(prompts)
            category = 'emotional_support'
        elif content_themes.get('work', 0) > 3:
            prompts = self.writing_prompts['reflection']
            prompt = random.choice(prompts)
            category = 'work_life_balance'
        else:
            category = random.choice(list(self.writing_prompts.keys()))
            prompts = self.writing_prompts[category]
            prompt = random.choice(prompts)
        
        return {
            'prompt': prompt,
            'category': category,
            'personalized': True,
            'insight': self._get_context_insight(mood_pattern, content_themes)
        }
    
    def _get_random_prompt(self) -> Dict:
        """Get a random prompt when no user history is available."""
        category = random.choice(list(self.writing_prompts.keys()))
        prompt = random.choice(self.writing_prompts[category])
        
        return {
            'prompt': prompt,
            'category': category,
            'personalized': False,
            'insight': "Start with this prompt to begin your journaling journey!"
        }
    
    def _analyze_mood_pattern(self, entries: List[Entry]) -> str:
        """Analyze mood patterns from recent entries."""
        if len(entries) < 3:
            return 'insufficient_data'
        
        moods = [entry.mood for entry in entries if entry.mood]
        if len(moods) < 3:
            return 'insufficient_data'
        
        # Simple pattern detection
        happy_count = moods.count('😊 Happy')
        sad_count = moods.count('😢 Sad')
        
        if happy_count > len(moods) * 0.6:
            return 'positive'
        elif sad_count > len(moods) * 0.6:
            return 'declining'
        elif sad_count > happy_count and moods[-1] in ['😢 Sad']:
            return 'declining'
        else:
            return 'stable'
    
    def _analyze_content_themes(self, entries: List[Entry]) -> Dict[str, int]:
        """Analyze content themes from recent entries."""
        themes = {
            'work': 0,
            'relationships': 0,
            'health': 0,
            'goals': 0,
            'gratitude': 0
        }
        
        work_keywords = ['work', 'job', 'office', 'meeting', 'project', 'deadline', 'colleague']
        relationship_keywords = ['friend', 'family', 'love', 'relationship', 'partner', 'parent', 'sibling']
        health_keywords = ['health', 'exercise', 'sleep', 'doctor', 'medicine', 'diet', 'fitness']
        goal_keywords = ['goal', 'plan', 'future', 'achieve', 'target', 'objective', 'dream']
        gratitude_keywords = ['grateful', 'thankful', 'appreciate', 'blessed', 'gratitude', 'thanks']
        
        for entry in entries:
            content = (entry.content or '').lower()
            for theme, keywords in [
                ('work', work_keywords),
                ('relationships', relationship_keywords),
                ('health', health_keywords),
                ('goals', goal_keywords),
                ('gratitude', gratitude_keywords)
            ]:
                if any(keyword in content for keyword in keywords):
                    themes[theme] += 1
        
        return themes
    
    def _get_context_insight(self, mood_pattern: str, content_themes: Dict[str, int]) -> str:
        """Get contextual insight based on analysis."""
        insights = []
        
        if mood_pattern == 'positive':
            insights.append("You've been in a positive mood lately - keep nurturing that!")
        elif mood_pattern == 'declining':
            insights.append("Consider focusing on self-care and emotional processing.")
        elif mood_pattern == 'stable':
            insights.append("Your emotional balance is healthy - maintain this stability.")
        
        dominant_theme = max(content_themes.items(), key=lambda x: x[1]) if content_themes else None
        if dominant_theme and dominant_theme[1] > 0:
            theme_insights = {
                'work': "Work seems to be a major focus - consider work-life balance.",
                'relationships': "Relationships are important to you - nurture those connections.",
                'health': "Health awareness is great - keep prioritizing your well-being.",
                'goals': "You're goal-oriented - celebrate your progress and plan next steps.",
                'gratitude': "Gratitude is a strength - this builds resilience and happiness."
            }
            insights.append(theme_insights.get(dominant_theme[0], ""))
        
        return " ".join(insights) if insights else "Continue exploring your thoughts and feelings."
    
    def get_mood_insights(self, mood: str) -> Dict:
        """Get insights and recommendations for a specific mood."""
        return self.mood_insights.get(mood, {
            'insights': ["Every mood is valid and worth exploring."],
            'prompts': ["How are you feeling right now?"],
            'activities': ["Write about your current state."]
        })
    
    def get_smart_suggestions(self, current_text: str, cursor_position: int = 0) -> Dict:
        """Get smart writing suggestions based on current text."""
        suggestions = []
        
        # Analyze text length and content
        text_lower = current_text.lower()
        word_count = len(current_text.split())
        
        if word_count < 10:
            # Just starting
            suggestions.extend(self.suggestion_templates['opening_lines'])
        elif word_count < 50:
            # Need more depth
            suggestions.extend(self.suggestion_templates['reflection_questions'])
        else:
            # Well-developed, suggest closing
            suggestions.extend(self.suggestion_templates['closing_thoughts'])
        
        # Context-specific suggestions
        if 'feel' in text_lower and word_count < 30:
            suggestions.append("Describe the physical sensations of this feeling.")
        
        if 'problem' in text_lower or 'challenge' in text_lower:
            suggestions.append("What resources or support could help with this challenge?")
        
        if 'grateful' in text_lower or 'thankful' in text_lower:
            suggestions.append("How did these blessings come into your life?")
        
        return {
            'suggestions': suggestions[:5],  # Limit to 5 suggestions
            'word_count': word_count,
            'context': self._analyze_text_context(current_text)
        }
    
    def _analyze_text_context(self, text: str) -> str:
        """Analyze the context of the current text."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['today', 'happened', 'did']):
            return 'daily_reflection'
        elif any(word in text_lower for word in ['feel', 'feeling', 'emotion']):
            return 'emotional_processing'
        elif any(word in text_lower for word in ['plan', 'goal', 'future', 'tomorrow']):
            return 'goal_setting'
        elif any(word in text_lower for word in ['grateful', 'thankful', 'appreciate']):
            return 'gratitude_practice'
        else:
            return 'general_reflection'
    
    def analyze_entry_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of entry text (simplified version)."""
        positive_words = [
            'happy', 'joy', 'excited', 'grateful', 'thankful', 'love', 'wonderful',
            'amazing', 'great', 'fantastic', 'excellent', 'beautiful', 'peaceful'
        ]
        negative_words = [
            'sad', 'angry', 'frustrated', 'disappointed', 'worried', 'anxious',
            'stressed', 'tired', 'difficult', 'hard', 'challenging', 'overwhelmed'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            sentiment = 'neutral'
            confidence = 0.5
        else:
            sentiment_ratio = positive_count / total_sentiment_words
            if sentiment_ratio > 0.6:
                sentiment = 'positive'
                confidence = min(sentiment_ratio, 1.0)
            elif sentiment_ratio < 0.4:
                sentiment = 'negative'
                confidence = min(1 - sentiment_ratio, 1.0)
            else:
                sentiment = 'neutral'
                confidence = 0.5
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'positive_words': positive_count,
            'negative_words': negative_count,
            'total_words': len(text.split())
        }
    
    def get_wellness_tips(self, mood: str, recent_entries: List[Entry] = None) -> List[str]:
        """Get personalized wellness tips based on mood and patterns."""
        base_tips = {
            '😊 Happy': [
                "Share your happiness with others - it's contagious!",
                "Document what led to this joy for future reference.",
                "Use this energy to tackle something you've been avoiding."
            ],
            '😢 Sad': [
                "Allow yourself to feel without judgment.",
                "Reach out to someone you trust.",
                "Engage in a comforting activity that usually helps."
            ],
            '😡 Angry': [
                "Channel this energy into physical activity.",
                "Write down your thoughts before speaking.",
                "Take deep breaths and count to ten."
            ],
            '😴 Tired': [
                "Prioritize rest over productivity today.",
                "Consider what's draining your energy.",
                "Plan a relaxing evening routine."
            ]
        }
        
        tips = base_tips.get(mood, ["Practice self-awareness and self-compassion."])
        
        # Add pattern-based tips
        if recent_entries and len(recent_entries) >= 5:
            mood_pattern = self._analyze_mood_pattern(recent_entries)
            if mood_pattern == 'declining':
                tips.append("Consider talking to a friend or professional about persistent negative feelings.")
            elif mood_pattern == 'positive':
                tips.append("Keep a gratitude journal to maintain this positive momentum.")
        
        return tips


# Global service instance
ai_features = AIFeaturesService()
