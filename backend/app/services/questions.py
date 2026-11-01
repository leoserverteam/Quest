import os
import yaml
from typing import Dict, Any, List
from watchfiles import awatch
import asyncio
from threading import Thread
from app.core.config import settings


class QuestionsService:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or settings.QUESTIONS_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Questions config not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._validate(data)
        self._config = data

    def _validate(self, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Config must be a dict")
        categories = data.get("categories", [])
        if not isinstance(categories, list):
            raise ValueError("categories must be a list")
        seen_cat = set()
        for cat in categories:
            if not isinstance(cat, dict):
                raise ValueError("category must be dict")
            cid = cat.get("id")
            if not cid or not isinstance(cid, str):
                raise ValueError("category.id required")
            if cid in seen_cat:
                raise ValueError(f"duplicate category id: {cid}")
            seen_cat.add(cid)
            if not cat.get("title"):
                raise ValueError(f"category {cid} missing title")
            questions = cat.get("questions", [])
            if not isinstance(questions, list):
                raise ValueError(f"category {cid}.questions must be list")
            seen_q = set()
            for q in questions:
                if not isinstance(q, dict):
                    raise ValueError(f"question in {cid} must be dict")
                qid = q.get("id")
                if not qid or not isinstance(qid, str):
                    raise ValueError(f"question.id required in {cid}")
                if qid in seen_q:
                    raise ValueError(f"duplicate question id {qid} in {cid}")
                seen_q.add(qid)
                if not q.get("title"):
                    raise ValueError(f"question {qid} missing title")
                qtype = q.get("type")
                allowed = {"text", "textarea", "boolean", "select", "multiselect", "number", "date", "url"}
                if qtype not in allowed:
                    raise ValueError(f"question {qid} has invalid type {qtype}")
                if qtype in ("select", "multiselect"):
                    opts = q.get("options")
                    if not isinstance(opts, list) or not opts:
                        raise ValueError(f"question {qid} of type {qtype} needs non-empty options")
                    for o in opts:
                        if not isinstance(o, dict) or not o.get("value") or not o.get("label"):
                            raise ValueError(f"question {qid} options must have value and label")

    def reload(self):
        self._load()

    def get_config(self) -> Dict[str, Any]:
        return self._config

    def get_categories(self) -> List[Dict[str, Any]]:
        return self._config.get("categories", [])

    def get_question_ids(self) -> set:
        ids = set()
        for cat in self.get_categories():
            for q in cat.get("questions", []):
                ids.add(q["id"])
        return ids


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
