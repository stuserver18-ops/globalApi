import os
import zipfile
import tempfile
from pathlib import Path
from typing import Generator
from fastapi import HTTPException

# Define allowed root directories (must be absolute and normalized)
ALLOWED_ROOTS = [
    Path("/home").resolve(),
    Path("/mnt/data").resolve(),
    Path("/tmp/explorer").resolve(),
]

def resolve_safe_path(subpath: str) -> Path:
    """Resolve a user-provided path ensuring it's under an allowed root."""
    if not subpath:
        return ALLOWED_ROOTS[0]  # Default to first allowed root

    target = Path(subpath).resolve()

    for root in ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail=f"Access to '{target}' is not allowed")

def generate_zip_from_folder(folder_path: Path) -> Generator[bytes, None, None]:
    """Stream ZIP archive of a folder as chunks of bytes."""
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name
    try:
        with zipfile.ZipFile(tmp_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(folder_path):
                for fname in files:
                    full = Path(root) / fname
                    arcname = full.relative_to(folder_path)
                    zf.write(full, arcname)

        with open(tmp_name, "rb") as f:
            while chunk := f.read(65536):
                yield chunk
    finally:
        try:
            os.unlink(tmp_name)
        except Exception:
            pass
