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
    
    def generate_entry_suggestions_with_search(self, mood: str = None, tags: str = None, category: str = None) -> str:
        """Generate enhanced writing prompts with web search context"""
        # Create more specific search queries based on mood
        mood_search_terms = {
            'happy': 'positive psychology gratitude journaling',
            'sad': 'emotional healing journaling prompts',
            'anxious': 'mindfulness anxiety journaling techniques',
            'angry': 'anger management journal writing exercises',
            'stressed': 'stress relief journaling methods',
            'excited': 'goal setting journaling prompts',
            'grateful': 'gratitude journaling exercises',
            'confused': 'self-reflection journaling prompts',
            'lonely': 'connection journaling activities',
            'tired': 'energy management journaling'
        }
        
        search_query = mood_search_terms.get(mood.lower(), f'journaling prompts for {mood or "general well-being"}')
        if category:
            search_query += f" {category}"
        
        search_results = self.search_web_for_context(search_query)
        
        # Enhanced prompt with more specific instructions
        prompt = f"""Generate 5 diverse and engaging journal writing prompts for someone feeling {mood or 'neutral'}."""
        
        if category:
            prompt += f" Focus on {category} themes."
        if tags:
            prompt += f" Incorporate these topics: {tags}."
        
        prompt += f"""
        
        Use these research insights for context:
        {json.dumps(search_results, indent=2)}
        
        Create prompts that are:
        1. **Specific and actionable** - Clear questions or statements
        2. **Emotionally intelligent** - Match the {mood or 'neutral'} mood appropriately
        3. **Therapeutically informed** - Based on psychological research
        4. **Varied in format** - Mix of questions, statements, and exercises
        5. **Personal growth oriented** - Encourage self-discovery and development
        
        Format each prompt with a clear heading and brief explanation.
        Include different types: reflective questions, creative exercises, gratitude prompts, and goal-setting activities.
        
        Make them feel personal, supportive, and evidence-based."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI suggestions unavailable: {str(e)}"
    
    def generate_personalized_suggestions(self, user_entries: List[Dict], mood: str = None, tags: str = None, category: str = None) -> str:
        """Generate personalized suggestions based on user's writing history"""
        # Analyze user's writing patterns
        if not user_entries:
            return self.generate_entry_suggestions_with_search(mood, tags, category)
        
        # Extract patterns from user's entries
        user_moods = [entry.get('mood', '').lower() for entry in user_entries if entry.get('mood')]
        user_categories = [entry.get('category', '').lower() for entry in user_entries if entry.get('category')]
        user_tags = []
        for entry in user_entries:
            if entry.get('tags'):
                user_tags.extend([tag.strip().lower() for tag in entry['tags'].split(',')])
        
        # Most common patterns
        common_mood = max(set(user_moods), key=user_moods.count) if user_moods else None
        common_category = max(set(user_categories), key=user_categories.count) if user_categories else None
        common_tags = [tag for tag in set(user_tags) if user_tags.count(tag) > 1]
        
        # Create personalized search query
        if common_mood:
            search_query = f"journaling patterns for {common_mood} mood"
        else:
            search_query = f"journaling prompts for {mood or 'general well-being'}"
        
        if category:
            search_query += f" {category}"
        
        search_results = self.search_web_for_context(search_query)
        
        # Enhanced personalized prompt
        prompt = f"""Generate 5 personalized journal writing prompts based on the user's writing patterns."""
        
        if mood:
            prompt += f" Current mood: {mood}."
        if category:
            prompt += f" Interest area: {category}."
        if tags:
            prompt += f" Topics: {tags}."
        
        # Add user patterns to prompt
        if common_mood:
            prompt += f" Note: User frequently writes when feeling {common_mood}."
        if common_category:
            prompt += f" Note: User often writes about {common_category}."
        if common_tags:
            prompt += f" Note: User commonly uses tags like: {', '.join(common_tags[:3])}."
        
        prompt += f"""
        
        Use these research insights for context:
        {json.dumps(search_results, indent=2)}
        
        Create prompts that are:
        1. **Personalized** - Reference their writing patterns and preferences
        2. **Progressive** - Build on their previous journaling themes
        3. **Therapeutically aligned** - Support their emotional journey
        4. **Varied approaches** - New angles on familiar themes
        5. **Growth-oriented** - Encourage deeper self-exploration
        
        Include a mix of:
        - Reflections on their common themes
        - New perspectives on familiar topics
        - Exercises that build on their interests
        - Prompts that explore their emotional patterns
        
        Make each prompt feel like it was written specifically for this user's journey."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Personalized suggestions unavailable: {str(e)}"
    
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
ai_service = AIService()
