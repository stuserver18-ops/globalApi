import os
import zipfile
import tempfile
from pathlib import Path
from typing import Generator, List
from fastapi import HTTPException

def resolve_safe_path(subpath: str) -> Path:
    # Get REAL allowed roots (resolved via CRUD function)
    from .allowed_root_crud import get_allowed_roots_as_paths  # adjust import as needed
    allowed_roots = get_allowed_roots_as_paths()  # Uses imported CRUD function
    if not allowed_roots:
        raise HTTPException(status_code=500, detail="No allowed roots configured")

    if not subpath:
        return allowed_roots[0]

    input_path = Path(subpath)

    # ABSOLUTE PATH HANDLING (your /home case)
    if input_path.is_absolute():
        # DO NOT resolve symlinks yet - validate first
        normalized_input = Path(os.path.normpath(str(input_path)))
        
        for root in allowed_roots:
            # Resolve root ONCE (it's trusted)
            resolved_root = root.resolve(strict=False)
            
            # Critical: Check containment BEFORE resolving input
            try:
                # Handles exact root matches AND subdirectories
                normalized_input.relative_to(resolved_root)
                # Only NOW resolve the full path (safe because validated)
                return normalized_input.resolve(strict=False)
            except ValueError:
                continue

        raise HTTPException(status_code=403, detail="Path not under any allowed root")

    # RELATIVE PATH HANDLING (unchanged but safer)
    if any(part == ".." for part in input_path.parts):
        raise HTTPException(status_code=400, detail="Path traversal ('..') is not allowed")

    for root in allowed_roots:
        candidate = root / input_path
        try:
            resolved_candidate = candidate.resolve(strict=False)
            resolved_root = root.resolve(strict=False)
            resolved_candidate.relative_to(resolved_root)  # Validates containment
            return resolved_candidate
        except (ValueError, OSError):
            continue

    raise HTTPException(status_code=403, detail="Path not under any allowed root")

# --- ZIP Streaming Utility ---

def generate_zip_from_folder(folder_path: Path) -> Generator[bytes, None, None]:
    """Stream a ZIP archive of the given folder."""
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name

    try:
        with zipfile.ZipFile(tmp_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, _, files in os.walk(folder_path):
                for fname in files:
                    full_path = Path(root_dir) / fname
                    arcname = full_path.relative_to(folder_path)
                    zf.write(full_path, arcname)

        with open(tmp_name, "rb") as f:
            while chunk := f.read(65536):  # 64 KiB chunks
                yield chunk
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass