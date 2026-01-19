import os
import json
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
        """Analyze the sentiment and emotional tone of an entry with structured output"""
        prompt = f"""Analyze this journal entry and provide a JSON response with:
        {{
            "sentiment": "positive/negative/neutral",
            "mood_score": -1.0 to 1.0,
            "emotions": ["emotion1", "emotion2", "emotion3"],
            "insights": "brief emotional journey analysis",
            "reflection_question": "thoughtful question for the writer"
        }}
        
        Entry: {text}
        
        Respond only with valid JSON."""
        
        try:
            response = self.model.generate_content(prompt)
            
            # Try to parse JSON response
            try:
                analysis_data = json.loads(response.text)
                return {
                    "sentiment": analysis_data.get("sentiment", "neutral"),
                    "mood_score": float(analysis_data.get("mood_score", 0.0)),
                    "emotions": json.dumps(analysis_data.get("emotions", [])),
                    "insights": analysis_data.get("insights", ""),
                    "reflection_question": analysis_data.get("reflection_question", ""),
                    "success": True
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "sentiment": "neutral",
                    "mood_score": 0.0,
                    "emotions": json.dumps([]),
                    "insights": response.text[:200],
                    "reflection_question": "",
                    "success": True
                }
                
        except Exception as e:
            return {
                "sentiment": "neutral",
                "mood_score": 0.0,
                "emotions": json.dumps([]),
                "insights": f"Sentiment analysis unavailable: {str(e)}",
                "reflection_question": "",
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
    
    def get_mood_trends(self, entries: List[Dict]) -> Dict[str, Any]:
        """Analyze mood trends from multiple entries"""
        if not entries:
            return {"trend": "no_data", "insights": "No entries to analyze"}
        
        # Extract mood scores
        mood_scores = [entry.get('mood_score', 0) for entry in entries if entry.get('mood_score') is not None]
        
        if not mood_scores:
            return {"trend": "no_scores", "insights": "No mood scores available"}
        
        avg_mood = sum(mood_scores) / len(mood_scores)
        recent_moods = mood_scores[-3:] if len(mood_scores) >= 3 else mood_scores
        recent_avg = sum(recent_moods) / len(recent_moods)
        
        # Determine trend
        if recent_avg > avg_mood + 0.1:
            trend = "improving"
        elif recent_avg < avg_mood - 0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "average_mood": avg_mood,
            "recent_average": recent_avg,
            "total_entries": len(entries),
            "analyzed_entries": len(mood_scores)
        }

# Global AI service instance
ai_service = AIService()
