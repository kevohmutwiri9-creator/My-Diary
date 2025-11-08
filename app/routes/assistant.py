"""AI Assistant Routes"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from app.services.assistant import (
    AssistantGenerationError,
    AssistantNotConfiguredError,
    DiaryAssistantService,
)
from app.models.entry import Entry

assistant_bp = Blueprint("assistant", __name__)


def _assistant_service() -> DiaryAssistantService:
    return DiaryAssistantService(current_user)


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@assistant_bp.route("/ask", methods=["POST"])
@login_required
def ask_assistant():
    try:
        payload = request.get_json(silent=True) or {}
        question = (payload.get("question") or "").strip()
        if len(question) < 3:
            return _json_error("Question too short", 400)

        service = _assistant_service()
        response = service.answer_question(
            question,
            context_days=current_app.config.get("ASSISTANT_CONTEXT_DAYS", 30),
        )
        return jsonify({"answer": response.text, "model": response.model})
    except AssistantNotConfiguredError as exc:
        return _json_error(str(exc), 503)
    except AssistantGenerationError as exc:
        current_app.logger.warning("Assistant generation error: %s", exc, exc_info=True)
        return _json_error(str(exc), 503)
    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.error("Unexpected assistant error: %s", exc, exc_info=True)
        return _json_error("Assistant unavailable", 500)


@assistant_bp.route("/summarize", methods=["POST"])
@login_required
def summarize_entry():
    try:
        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        if not content:
            return _json_error("Entry content is required", 400)

        service = _assistant_service()
        result = service.summarize_entry(
            content,
            title=payload.get("title"),
            instructions=payload.get("instructions"),
        )
        return jsonify({"summary": result["summary"], "takeaways": result["takeaways"], "model": result["model"]})
    except AssistantNotConfiguredError as exc:
        return _json_error(str(exc), 503)
    except AssistantGenerationError as exc:
        current_app.logger.warning("Assistant summary error: %s", exc, exc_info=True)
        return _json_error(str(exc), 503)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Unexpected summary error: %s", exc, exc_info=True)
        return _json_error("Assistant unavailable", 500)


@assistant_bp.route("/mood", methods=["POST"])
@login_required
def infer_mood():
    try:
        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        if not content:
            return _json_error("Entry content is required", 400)

        service = _assistant_service()
        result = service.infer_mood(content)
        return jsonify(result)
    except AssistantNotConfiguredError as exc:
        return _json_error(str(exc), 503)
    except AssistantGenerationError as exc:
        current_app.logger.warning("Assistant mood error: %s", exc, exc_info=True)
        return _json_error(str(exc), 503)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Unexpected mood error: %s", exc, exc_info=True)
        return _json_error("Assistant unavailable", 500)


@assistant_bp.route("/tags", methods=["POST"])
@login_required
def suggest_tags():
    try:
        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        if not content:
            return _json_error("Entry content is required", 400)

        service = _assistant_service()
        result = service.suggest_tags(
            content,
            max_tags=int(payload.get("max_tags", 5)),
        )
        return jsonify(result)
    except AssistantNotConfiguredError as exc:
        return _json_error(str(exc), 503)
    except AssistantGenerationError as exc:
        current_app.logger.warning("Assistant tags error: %s", exc, exc_info=True)
        return _json_error(str(exc), 503)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Unexpected tags error: %s", exc, exc_info=True)
        return _json_error("Assistant unavailable", 500)


@assistant_bp.route("/prompts", methods=["POST"])
@login_required
def suggest_prompts():
    try:
        payload = request.get_json(silent=True) or {}
        days = int(payload.get("context_days", current_app.config.get("ASSISTANT_PROMPT_DAYS", 14)))
        suggestions = int(payload.get("count", 3))

        service = _assistant_service()
        result = service.suggest_prompts(context_days=days, suggestions=suggestions)
        return jsonify(result)
    except AssistantNotConfiguredError as exc:
        return _json_error(str(exc), 503)
    except AssistantGenerationError as exc:
        current_app.logger.warning("Assistant prompts error: %s", exc, exc_info=True)
        return _json_error(str(exc), 503)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Unexpected prompts error: %s", exc, exc_info=True)
        return _json_error("Assistant unavailable", 500)


@assistant_bp.route("/latest", methods=["GET"])
@login_required
def latest_entry_snapshot():
    entry = (
        Entry.query
        .filter_by(user_id=current_user.id)
        .order_by(Entry.created_at.desc())
        .first()
    )
    if not entry:
        return jsonify({}), 200

    return jsonify(
        {
            "id": entry.id,
            "title": entry.title,
            "content": entry.content,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
    )
