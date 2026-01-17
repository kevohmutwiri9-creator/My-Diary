import os
import google.generativeai as genai
from typing import Optional, List, Dict, Any

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

class AIService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_entry_suggestions(self, mood: Optional[str] = None, tags: Optional[str] = None, category: Optional[str] = None) -> str:
        """Generate writing prompts based on mood, tags, and category"""
        prompt = f"Generate 3-5 thoughtful journal writing prompts for someone feeling {mood or 'neutral'}"
        if category:
            prompt += f" interested in {category} topics"
        if tags:
            prompt += f" related to: {tags}"
        prompt += ". Make them personal and introspective."
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI suggestions unavailable: {str(e)}"
    
    def analyze_entry_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze the sentiment and emotional tone of an entry"""
        prompt = f"""Analyze the emotional tone of this journal entry and provide:
        1. Overall sentiment (positive, negative, neutral)
        2. Key emotions detected
        3. A brief summary of the emotional journey
        4. One thoughtful reflection question
        
        Entry text: {text}"""
        
        try:
            response = self.model.generate_content(prompt)
            return {
                "analysis": response.text,
                "success": True
            }
        except Exception as e:
            return {
                "analysis": f"Sentiment analysis unavailable: {str(e)}",
                "success": False
            }
    
    def generate_wellness_insights(self, entries_text: List[str]) -> str:
        """Generate wellness insights from multiple entries"""
        combined_text = "\n\n".join(entries_text[-5:])  # Last 5 entries
        
        prompt = f"""Based on these recent journal entries, provide personalized wellness insights:
        1. Emotional patterns and trends
        2. Positive coping strategies observed
        3. Areas that might need attention
        4. Gentle suggestions for emotional well-being
        
        Entries: {combined_text}"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Wellness insights unavailable: {str(e)}"
    
    def suggest_mood_improvement(self, mood: str, entry_text: str) -> str:
        """Suggest activities based on current mood and entry content"""
        prompt = f"""Based on someone feeling {mood} who wrote: "{entry_text[:200]}..."
        Suggest 3-4 specific, actionable activities that could help improve their mood.
        Make them practical and personalized to their situation."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Mood suggestions unavailable: {str(e)}"

# Global AI service instance
ai_service = AIService()
