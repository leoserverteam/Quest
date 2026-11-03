"""Helpers for merging standard and user-pool questions into a profile.

Pool items are stored as a snapshot on ``ProfileQuestionPool``.  Question ids
for pool items are deterministic (based on the pool id and item id), so answers
survive detaching and re-attaching the same pool.
"""
import copy
import hashlib
from typing import Any, Dict, Iterable, List, Optional

from app.services.questions import (
    CHOICE_TYPES,
    QuestionValidationError,
    normalize_options,
    normalize_question_type,
    questions_service,
)

POOL_QUESTION_PREFIX = "pool_"


def pool_question_id(pool_id: Any, item_id: str) -> str:
    """Build a stable, compact question id for a pool item."""
    raw = f"{pool_id}:{item_id}".encode("utf-8")
    return POOL_QUESTION_PREFIX + hashlib.sha1(raw).hexdigest()[:20]


def snapshot_items(snapshot: Any) -> List[Dict[str, Any]]:
    """Return the item list from a snapshot in either old or new format."""
    if isinstance(snapshot, dict):
        items = snapshot.get("items")
        return items if isinstance(items, list) else []
    if isinstance(snapshot, list):
        return snapshot
    return []


def snapshot_name(snapshot: Any) -> Optional[str]:
    if isinstance(snapshot, dict):
        name = snapshot.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def make_snapshot(pool) -> Dict[str, Any]:
    """Create a frozen snapshot of a pool for attaching to a profile."""
    items = []
    for item in sorted(pool.items, key=lambda x: (x.position or 0, str(x.id))):
        qtype = normalize_question_type(item.type)
        options = None
        if qtype in CHOICE_TYPES:
            options = normalize_options(item.options)
        items.append(
            {
                "item_id": item.item_id,
                "question_id": pool_question_id(pool.id, item.item_id),
                "title": item.title,
                "description": item.description,
                "type": qtype,
                "required": bool(item.required),
                "options": copy.deepcopy(options),
                "position": item.position or 0,
            }
        )
    return {"name": pool.name, "items": items}


def build_profile_categories(profile) -> List[Dict[str, Any]]:
    """Standard config categories followed by attached pool categories."""
    categories = copy.deepcopy(questions_service.get_categories())

    links = list(getattr(profile, "profile_pools", []) or [])
    links.sort(key=lambda link: (link.position or 0, str(link.id)))
    for link in links:
        items = snapshot_items(link.snapshot)
        questions: List[Dict[str, Any]] = []
        for item in sorted(items, key=lambda x: (x.get("position") or 0, str(x.get("item_id", "")))):
            item_id = item.get("item_id")
            if not isinstance(item_id, str) or not item_id:
                continue
            try:
                qtype = normalize_question_type(item.get("type"))
            except QuestionValidationError:
                continue
            options = item.get("options")
            if qtype in CHOICE_TYPES:
                try:
                    options = normalize_options(options)
                except QuestionValidationError:
                    continue
            else:
                options = None

            questions.append(
                {
                    "id": item.get("question_id")
                    or pool_question_id(link.pool_id or f"link:{link.id}", item_id),
                    "title": item.get("title") or "Вопрос",
                    "description": item.get("description"),
                    "type": qtype,
                    "required": bool(item.get("required", False)),
                    "options": options,
                    "source": "pool",
                    "pool_link_id": str(link.id),
                    "pool_id": str(link.pool_id) if link.pool_id else None,
                    "pool_item_id": item_id,
                }
            )

        if not questions:
            continue
        title = snapshot_name(link.snapshot)
        if not title:
            pool = getattr(link, "pool", None)
            title = getattr(pool, "name", None) if pool is not None else None
        categories.append(
            {
                "id": f"pool-{link.id}",
                "title": title or "Мои вопросы",
                "source": "pool",
                "pool_link_id": str(link.id),
                "questions": questions,
            }
        )

    return categories


def build_question_index(categories: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        for question in cat.get("questions", []):
            qid = question.get("id")
            if qid:
                index[qid] = question
    return index


def normalize_answer_value(question: Dict[str, Any], value: Any) -> Any:
    """Validate/normalize an answer according to its question definition.

    Empty answers are represented as ``None`` (single values) or ``[]`` (multi).
    """
    qtype = question.get("type")
    options = question.get("options") or []
    allowed_values = {o["value"] for o in options if isinstance(o, dict) and o.get("value")}

    if qtype == "select":
        if value is None or value == "":
            return None
        if isinstance(value, list):
            value = value[0] if value else None
        if not isinstance(value, str) or value not in allowed_values:
            raise QuestionValidationError("Invalid option value")
        return value

    if qtype == "multiselect":
        if value is None or value == "":
            return []
        if not isinstance(value, list):
            value = [value]
        result = []
        for item in value:
            if not isinstance(item, str) or item not in allowed_values:
                raise QuestionValidationError("Invalid option value")
            if item not in result:
                result.append(item)
        return result

    if qtype == "boolean":
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "on"}
        return bool(value)

    if qtype == "number":
        if value is None or value == "":
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise QuestionValidationError("Invalid number")
        return int(number) if number.is_integer() else number

    if value is None:
        return None
    if isinstance(value, (list, dict)):
        raise QuestionValidationError("Invalid answer value")
    return str(value)
