from typing import List, Dict, Any, Optional
from pathlib import Path
from crud import add, update, delete, get

TABLE_NAME = "allowed_roots"
APP_NAME = "file_explorer"  # matches your DB name


def normalize_path(path: str) -> str:
    """Normalize and validate a filesystem path."""
    try:
        return str(Path(path).resolve())
    except Exception as e:
        raise ValueError(f"Invalid path: {path}") from e


def create_allowed_root(
    path: str,
    description: Optional[str] = None,
    is_allowed: bool = True  # <-- new parameter
) -> int:
    normalized = normalize_path(path)
    data = {
        "path": normalized,
        "is_allowed": is_allowed
    }
    if description is not None:
        data["description"] = description
    return add(TABLE_NAME, data, app_name=APP_NAME)


def get_all_allowed_roots() -> List[Dict[str, Any]]:
    """Fetch all allowed root paths."""
    return get(TABLE_NAME, app_name=APP_NAME)


def get_allowed_roots_as_paths() -> List[Path]:
    """Helper: Return list of Path objects for current allowed roots."""
    records = get_all_allowed_roots()
    return [Path(rec["path"]).resolve() for rec in records]


def update_allowed_root(
    root_id: int,
    path: Optional[str] = None,
    description: Optional[str] = None,
    is_allowed: Optional[bool] = None  # <-- new parameter
) -> int:
    data = {}
    if path is not None:
        data["path"] = normalize_path(path)
    if description is not None:
        data["description"] = description
    if is_allowed is not None:
        data["is_allowed"] = is_allowed
    if not data:
        raise ValueError("At least one field must be provided")
    return update(TABLE_NAME, data, where="id = %s", params=(root_id,), app_name=APP_NAME)


def delete_allowed_root(root_id: int) -> int:
    """Delete an allowed root by ID."""
    return delete(TABLE_NAME, where="id = %s", params=(root_id,), app_name=APP_NAME)
