import os
import re
from pathlib import Path
from typing import Optional


def sanitize_slug(slug: str) -> str:
    slug = slug.strip().lower()
    slug = re.sub(r"[^a-z0-9\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def safe_filename(filename: str) -> str:
    # only keep basename, remove path traversal
    name = os.path.basename(filename)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
