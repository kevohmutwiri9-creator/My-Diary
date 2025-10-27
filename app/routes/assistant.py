"""AI Assistant Routes"""
import google.generativeai as genai
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.entry import Entry
from datetime import datetime, timedelta
import os

assistant_bp = Blueprint('assistant', __name__)

def get_entries_context(days=30):
    """Get recent entries as context"""
    date_threshold = datetime.utcnow() - timedelta(days=days)
    entries = Entry.query.filter(
        Entry.user_id == current_user.id,
        Entry.created_at >= date_threshold
    ).order_by(Entry.created_at.desc()).all()
    return "\n\n".join(
        f"{e.created_at.date()}: {e.content[:200]}{'...' if len(e.content) > 200 else ''}"
        for e in entries
    )

@assistant_bp.route('/ask', methods=['POST'])
@login_required
def ask_assistant():
    try:
        if not current_app.config['GEMINI_API_KEY']:
            return jsonify({"error": "Assistant not configured"}), 503
            
        user_question = request.json.get('question', '').strip()
        if len(user_question) < 3:
            return jsonify({"error": "Question too short"}), 400
            
        context = get_entries_context()
        
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        model_candidates = [
            'models/gemini-2.5-flash',
            'models/gemini-2.5-pro',
            'models/gemini-flash-latest',
            'models/gemini-pro-latest'
        ]
        last_error = None

        for model_id in model_candidates:
            try:
                current_app.logger.debug("Attempting Gemini model: %s", model_id)
                model = genai.GenerativeModel(model_id)
                response = model.generate_content(
                    f"""Role: Private diary assistant. Be concise and specific.
                    Recent Entries:
                    {context}
                    
                    Question: {user_question}
                    Answer:"""
                )
                return jsonify({"answer": response.text, "model": model_id})
            except Exception as inner_err:
                last_error = inner_err
                current_app.logger.warning(
                    "Assistant generation failed using %s: %s",
                    model_id,
                    inner_err,
                    exc_info=True
                )
                continue

        error_message = "Assistant temporarily unavailable"
        if last_error:
            error_message = f"Assistant error: {last_error}"
        return jsonify({"error": error_message}), 503
    except KeyError as key_err:
        current_app.logger.error("Assistant configuration error: missing %s", key_err)
        return jsonify({"error": "Assistant not configured"}), 503
    except Exception as e:
        current_app.logger.error("Assistant error: %s", e, exc_info=True)
        return jsonify({"error": "Assistant unavailable"}), 500
