import copy
import os
from typing import Any, Dict, List, Optional

import yaml
from watchfiles import awatch
import asyncio
from threading import Thread
from app.core.config import settings


# Canonical question types used by config, pools, API, and the frontend.
# `select` is a single-choice question, `multiselect` is a multiple-choice one.
QUESTION_TYPES = frozenset(
    {"text", "textarea", "boolean", "select", "multiselect", "number", "date", "url"}
)
CHOICE_TYPES = frozenset({"select", "multiselect"})

# Accept a few historic/alternative spellings, but always persist canonical types.
TYPE_ALIASES = {
    "single_choice": "select",
    "single": "select",
    "radio": "select",
    "choice": "select",
    "multiple_choice": "multiselect",
    "multiple": "multiselect",
    "checkbox": "multiselect",
    "multi_select": "multiselect",
    "multi": "multiselect",
}


class QuestionValidationError(ValueError):
    """Raised when a question definition is invalid."""


def normalize_question_type(value: Optional[str]) -> str:
    if not isinstance(value, str):
        raise QuestionValidationError("Question type is required")
    normalized = value.strip().lower()
    normalized = TYPE_ALIASES.get(normalized, normalized)
    if normalized not in QUESTION_TYPES:
        raise QuestionValidationError(f"Unsupported question type: {value}")
    return normalized


def normalize_options(options: Any) -> List[Dict[str, str]]:
    """Validate and normalize choice options.

    Accepts the canonical list of ``{value, label}`` objects.  Plain strings are
    also accepted for backwards compatibility and become both value and label.
    """
    if not isinstance(options, list) or not options:
        raise QuestionValidationError("Choice questions require non-empty options")

    result: List[Dict[str, str]] = []
    seen_values = set()
    for raw in options:
        if isinstance(raw, str):
            value = label = raw
        elif isinstance(raw, dict):
            value = raw.get("value")
            label = raw.get("label")
        else:
            raise QuestionValidationError("Each option must be an object or string")

        if not isinstance(value, str) or not value.strip():
            raise QuestionValidationError("Option value must not be empty")
        if not isinstance(label, str) or not label.strip():
            raise QuestionValidationError("Option label must not be empty")

        value = value.strip()
        label = label.strip()
        if len(value) > 64:
            raise QuestionValidationError("Option value is too long (max 64)")
        if len(label) > 255:
            raise QuestionValidationError("Option label is too long (max 255)")
        if value in seen_values:
            raise QuestionValidationError(f"Duplicate option value: {value}")
        seen_values.add(value)
        result.append({"value": value, "label": label})

    return result


def get_question_ids(categories: List[Dict[str, Any]]) -> set:
    ids = set()
    for cat in categories:
        for q in cat.get("questions", []):
            ids.add(q["id"])
    return ids


class QuestionsService:
    def __init__(self, config_path: str = None):
        self.config_path = (
            config_path
            or settings.QUESTIONS_CONFIG_PATH
            or "/app/config/questions.yaml"
        )
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Questions config not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._validate(data)
        self._config = self._normalize(data)

    def _validate(self, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise QuestionValidationError("Config must be a dict")
        categories = data.get("categories", [])
        if not isinstance(categories, list):
            raise QuestionValidationError("categories must be a list")
        seen_cat = set()
        seen_questions = set()
        for cat in categories:
            if not isinstance(cat, dict):
                raise QuestionValidationError("category must be dict")
            cid = cat.get("id")
            if not cid or not isinstance(cid, str):
                raise QuestionValidationError("category.id required")
            if cid in seen_cat:
                raise QuestionValidationError(f"duplicate category id: {cid}")
            seen_cat.add(cid)
            if not cat.get("title"):
                raise QuestionValidationError(f"category {cid} missing title")
            questions = cat.get("questions", [])
            if not isinstance(questions, list):
                raise QuestionValidationError(f"category {cid}.questions must be list")
            for q in questions:
                if not isinstance(q, dict):
                    raise QuestionValidationError(f"question in {cid} must be dict")
                qid = q.get("id")
                if not qid or not isinstance(qid, str):
                    raise QuestionValidationError(f"question.id required in {cid}")
                if qid in seen_questions:
                    raise QuestionValidationError(f"duplicate question id {qid}")
                seen_questions.add(qid)
                if not q.get("title"):
                    raise QuestionValidationError(f"question {qid} missing title")
                qtype = normalize_question_type(q.get("type"))
                if qtype in CHOICE_TYPES:
                    normalize_options(q.get("options"))

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = copy.deepcopy(data)
        for cat in normalized.get("categories", []):
            for q in cat.get("questions", []):
                q["type"] = normalize_question_type(q.get("type"))
                if q["type"] in CHOICE_TYPES:
                    q["options"] = normalize_options(q.get("options"))
                else:
                    q.pop("options", None)
                q["required"] = bool(q.get("required", False))
        return normalized

    def reload(self):
        self._load()

    def get_config(self) -> Dict[str, Any]:
        return self._config

    def get_categories(self) -> List[Dict[str, Any]]:
        return self._config.get("categories", [])

    def get_question_ids(self) -> set:
        return get_question_ids(self.get_categories())


questions_service = QuestionsService()


def start_watcher():
    async def _watch():
        async for changes in awatch(os.path.dirname(questions_service.config_path) or "."):
            # reload on change
            try:
                questions_service.reload()
                print("[questions] config reloaded")
            except Exception as e:
                print(f"[questions] reload error: {e}")

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_watch())

    t = Thread(target=_run, daemon=True)
    t.start()
    return t
