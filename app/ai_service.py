import os
import json
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

class AIService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    def search_web_for_context(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Simulate web search for context (in real implementation, use actual search API)"""
        # This is a placeholder - in production, integrate with real search API
        # like Google Custom Search API, Bing Search API, or SerpApi
        search_results = [
            {
                "title": f"Research on {query}",
                "snippet": f"Recent studies show that understanding {query} can improve emotional well-being.",
                "url": f"https://example.com/research-{query.lower().replace(' ', '-')}"
            },
            {
                "title": f"{query} Management Techniques",
                "snippet": f"Evidence-based techniques for managing {query} include mindfulness, exercise, and social support.",
                "url": f"https://example.com/techniques-{query.lower().replace(' ', '-')}"
            }
        ]
        return search_results[:max_results]
    
    def generate_entry_suggestions_with_search(self, mood: Optional[str] = None, tags: Optional[str] = None, category: Optional[str] = None) -> str:
        """Generate writing prompts with web search context"""
        search_query = f"journaling prompts for {mood or 'general well-being'}"
        if category:
            search_query += f" {category}"
        
        search_results = self.search_web_for_context(search_query)
        
        prompt = f"""Generate 3-5 thoughtful journal writing prompts for someone feeling {mood or 'neutral'}"""
        
        if category:
            prompt += f" interested in {category} topics"
        if tags:
            prompt += f" related to: {tags}"
        
        prompt += f"""
        
        Use these research insights for context:
        {json.dumps(search_results, indent=2)}
        
        Make the prompts personal, introspective, and evidence-based. Incorporate relevant psychological concepts from the research."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI suggestions unavailable: {str(e)}"
    
    def analyze_entry_sentiment_with_context(self, text: str, user_mood_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Analyze sentiment with web search for psychological context"""
        # Detect key themes in the entry
        themes_prompt = f"""Extract 3-5 key emotional themes from this journal entry:
        {text}
        
        Return only the themes as a simple list."""
        
        try:
            themes_response = self.model.generate_content(themes_prompt)
            themes = [theme.strip() for theme in themes_response.text.split('\n') if theme.strip()]
        except:
            themes = []
        
        # Search for psychological context
        context_searches = []
        for theme in themes[:2]:  # Limit to top 2 themes
            context_searches.extend(self.search_web_for_context(f"{theme} psychology emotional well-being", 2))
        
        # Build enhanced analysis prompt
        prompt = f"""Analyze this journal entry with psychological context:
        
        Entry: {text}
        
        Psychological Context:
        {json.dumps(context_searches, indent=2)}
        
        Provide a JSON response with:
        {{
            "sentiment": "positive/negative/neutral",
            "mood_score": -1.0 to 1.0,
            "emotions": ["emotion1", "emotion2", "emotion3"],
            "insights": "brief psychological analysis incorporating research",
            "reflection_question": "thoughtful question based on psychological principles",
            "themes_found": ["theme1", "theme2"],
            "recommendations": ["actionable recommendation 1", "actionable recommendation 2"]
        }}
        
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
                    "themes_found": json.dumps(analysis_data.get("themes_found", [])),
                    "recommendations": json.dumps(analysis_data.get("recommendations", [])),
                    "context_sources": json.dumps([result.get("url", "") for result in context_searches]),
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
                    "themes_found": json.dumps(themes),
                    "recommendations": json.dumps([]),
                    "context_sources": json.dumps([]),
                    "success": True
                }
                
        except Exception as e:
            return {
                "sentiment": "neutral",
                "mood_score": 0.0,
                "emotions": json.dumps([]),
                "insights": f"Enhanced analysis unavailable: {str(e)}",
                "reflection_question": "",
                "themes_found": json.dumps([]),
                "recommendations": json.dumps([]),
                "context_sources": json.dumps([]),
                "success": False
            }
    
    def generate_wellness_insights_with_research(self, entries_text: List[str]) -> str:
        """Generate wellness insights with web search for current research"""
        combined_text = "\n\n".join(entries_text[-5:])  # Last 5 entries
        
        # Search for current wellness research
        research_topics = [
            "journaling mental health benefits 2024",
            "emotional regulation techniques evidence-based",
            "mindfulness journaling research"
        ]
        
        all_research = []
        for topic in research_topics:
            all_research.extend(self.search_web_for_context(topic, 2))
        
        prompt = f"""Based on these recent journal entries and current psychological research, provide personalized wellness insights:
        
        Entries: {combined_text}
        
        Current Research:
        {json.dumps(all_research, indent=2)}
        
        Include:
        1. Emotional patterns and trends
        2. Evidence-based coping strategies observed
        3. Areas that might need attention
        4. Gentle suggestions incorporating current research findings
        5. Specific techniques backed by psychological studies"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Enhanced wellness insights unavailable: {str(e)}"
    
    def suggest_mood_improvement_with_research(self, mood: str, entry_text: str) -> str:
        """Suggest activities based on current mood with evidence-based research"""
        # Search for evidence-based mood improvement strategies
        search_query = f"evidence-based techniques for {mood} mood improvement"
        research_results = self.search_web_for_context(search_query, 3)
        
        prompt = f"""Based on someone feeling {mood} who wrote: "{entry_text[:200]}..."
        
        Using this current research:
        {json.dumps(research_results, indent=2)}
        
        Suggest 3-4 specific, evidence-based activities that could help improve their mood.
        For each suggestion, include:
        - The activity
        - Brief evidence/research backing
        - How to implement it
        
        Make them practical and personalized to their situation."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Research-based mood suggestions unavailable: {str(e)}"
    
    def get_mood_trends_with_research(self, entries: List[Dict]) -> Dict[str, Any]:
        """Analyze mood trends with psychological research context"""
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
            research_query = "improving emotional well-being psychology"
        elif recent_avg < avg_mood - 0.1:
            trend = "declining"
            research_query = "managing declining mood psychology help"
        else:
            trend = "stable"
            research_query = "emotional stability maintenance psychology"
        
        # Get relevant research
        research_results = self.search_web_for_context(research_query, 2)
        
        return {
            "trend": trend,
            "average_mood": avg_mood,
            "recent_average": recent_avg,
            "total_entries": len(entries),
            "analyzed_entries": len(mood_scores),
            "research_context": json.dumps(research_results),
            "insights": f"Based on psychological research, your mood is {trend}. Consider evidence-based strategies for emotional regulation."
        }

# Global AI service instance
ai_service = AIService()()
