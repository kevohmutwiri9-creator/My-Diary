from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import google.generativeai as genai
from flask import current_app

from app.models.entry import Entry


class AssistantNotConfiguredError(RuntimeError):
    """Raised when the Gemini API key or models are unavailable."""


class AssistantGenerationError(RuntimeError):
    """Raised when the AI generation pipeline fails."""


@dataclass
class AssistantResponse:
    """Structured response from the AI assistant."""

    text: str
    model: str


class DiaryAssistantService:
    """Encapsulates Gemini-powered diary assistant behaviours."""

    def __init__(self, user) -> None:
        self.user = user
        self.logger = current_app.logger
        self.api_key = current_app.config.get("GEMINI_API_KEY")
        self.model_candidates: List[str] = current_app.config.get(
            "ASSISTANT_MODEL_CANDIDATES",
            [
                "models/gemini-2.5-flash",
                "models/gemini-2.5-pro",
                "models/gemini-flash-latest",
                "models/gemini-pro-latest",
            ],
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def answer_question(self, question: str, context_days: int = 30) -> AssistantResponse:
        prompt = self._build_chat_prompt(question, context_days)
        return self._generate(prompt, temperature=0.4)

    def summarize_entry(
        self,
        entry_content: str,
        title: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> Dict[str, object]:
        prompt = (
            "You are a reflective diary assistant. Produce a concise summary and three key takeaways "
            "for the provided private diary entry. Respond strictly as JSON with the following shape: "
            '{"summary": str, "takeaways": [str, str, str]}.'
        )
        if title:
            prompt += f"\nEntry title: {title}"
        if instructions:
            prompt += f"\nFollow these additional user instructions: {instructions.strip()}"
        prompt += f"\nEntry content:\n{entry_content.strip()}"

        response = self._generate(prompt, temperature=0.35)
        data = self._extract_json_object(response.text)
        if not data or "summary" not in data or "takeaways" not in data:
            raise AssistantGenerationError("Unable to parse summary output from assistant")
        # Normalise takeaways to strings
        takeaways = [str(item).strip() for item in data.get("takeaways", []) if str(item).strip()]
        return {
            "summary": str(data["summary"]).strip(),
            "takeaways": takeaways[:3],
            "model": response.model,
        }

    def infer_mood(self, entry_content: str) -> Dict[str, object]:
        prompt = (
            "You analyse diary entries to infer emotion. Reply strictly as JSON with: "
            '{"mood_label": str, "confidence": number between 0 and 1, "reasoning": str}. '
            "Allowed mood labels include Happy, Sad, Anxious, Angry, Relaxed, Tired, Grateful, Confused, Neutral. "
            "Choose the closest match."
        )
        prompt += f"\nDiary entry:\n{entry_content.strip()}"

        response = self._generate(prompt, temperature=0.3)
        data = self._extract_json_object(response.text)
        if not data or "mood_label" not in data:
            raise AssistantGenerationError("Unable to parse mood analysis output from assistant")
        return {
            "mood_label": str(data["mood_label"]).strip(),
            "confidence": float(data.get("confidence", 0)),
            "reasoning": str(data.get("reasoning", "")).strip(),
            "model": response.model,
        }

    def suggest_tags(self, entry_content: str, max_tags: int = 5) -> Dict[str, object]:
        prompt = (
            "Read the diary entry and suggest concise single or two-word themes suitable as tags. "
            'Reply strictly as JSON with shape: {"tags": [ {"label": str, "confidence": number } ]}. '
            "Return at most five tags and avoid duplicates or generic words like 'diary' or 'entry'."
        )
        prompt += f"\nEntry:\n{entry_content.strip()}"

        response = self._generate(prompt, temperature=0.45)
        data = self._extract_json_object(response.text)
        tags: List[Dict[str, object]] = []
        tag_items = data.get("tags", []) if isinstance(data, dict) else []
        for item in tag_items:
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            confidence = item.get("confidence", 0)
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                confidence_value = 0.0
            tags.append({"label": label, "confidence": round(confidence_value, 2)})
            if len(tags) >= max_tags:
                break
        if not tags:
            raise AssistantGenerationError("Assistant did not return any tag suggestions")
        return {
            "tags": tags,
            "model": response.model,
        }

    def suggest_prompts(self, context_days: int = 14, suggestions: int = 3) -> Dict[str, object]:
        recent_insights = self._get_recent_highlights(days=context_days)
        prompt = (
            "Generate journaling prompt suggestions tailored to the user based on their recent diary highlights. "
            'Reply strictly as JSON with the shape: {"prompts": [str, ...]} with concise prompts.'
        )
        prompt += f"\nRecent highlights:\n{recent_insights or 'No recent entries provided.'}"
        response = self._generate(prompt, temperature=0.6)
        data = self._extract_json_object(response.text)
        prompts = [str(item).strip() for item in data.get("prompts", []) if str(item).strip()]
        if not prompts:
            raise AssistantGenerationError("Assistant did not return any prompt suggestions")
        return {
            "prompts": prompts[:suggestions],
            "model": response.model,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_chat_prompt(self, question: str, context_days: int) -> str:
        context = self._get_recent_highlights(days=context_days)
        return (
            "Role: You are a concise, supportive diary assistant. Answer the user's question using the context below.\n"
            "If the context is empty, give a general but practical journaling answer.\n"
            f"User question: {question}\n"
            f"Context:\n{context if context else 'No recent entries available.'}\n"
            "Answer:"
        )

    def _get_recent_highlights(self, days: int = 30, limit: int = 8) -> str:
        date_threshold = datetime.utcnow() - timedelta(days=days)
        entries = (
            Entry.query
            .filter(Entry.user_id == self.user.id, Entry.created_at >= date_threshold)
            .order_by(Entry.created_at.desc())
            .limit(limit)
            .all()
        )
        highlights: List[str] = []
        for entry in entries:
            snippet = (entry.content or "").strip().replace("\n", " ")
            snippet = snippet[:400] + ("..." if len(snippet) > 400 else "")
            highlights.append(f"- {entry.created_at.strftime('%Y-%m-%d')}: {snippet}")
        return "\n".join(highlights)

    def _generate(self, prompt: str, *, temperature: float = 0.5) -> AssistantResponse:
        if not self.api_key:
            raise AssistantNotConfiguredError("Gemini API key not configured")

        genai.configure(api_key=self.api_key)
        last_error: Optional[Exception] = None

        for model_id in self.model_candidates:
            try:
                self.logger.debug("Assistant invoking model %s", model_id)
                model = genai.GenerativeModel(model_id)
                response = model.generate_content(prompt, generation_config={"temperature": temperature})
                if not getattr(response, "text", None):
                    raise AssistantGenerationError("Empty response from assistant")
                return AssistantResponse(text=response.text, model=model_id)
            except Exception as exc:  # pragma: no cover - defensive logging
                last_error = exc
                self.logger.warning("Assistant model %s failed: %s", model_id, exc, exc_info=True)
                continue

        raise AssistantGenerationError(f"All assistant models failed: {last_error}")

    @staticmethod
    def _extract_json_object(raw_text: str) -> Dict[str, object]:
        if not raw_text:
            return {}
        text = raw_text.strip()
        # Remove surrounding markdown code fences if present
        fence_match = re.search(r"```(?:json)?\s*(.*)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Attempt to find first JSON object in text
            brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(1))
                except json.JSONDecodeError:
                    return {}
        return {}
