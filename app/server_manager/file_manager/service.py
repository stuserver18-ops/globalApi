import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Generator
from fastapi import HTTPException
from .utils import resolve_safe_path, generate_zip_from_folder, ALLOWED_ROOTS

# Helper function to determine which root a path belongs to
def _get_current_root(full_path: Path) -> Path:
    """Find which allowed root contains the given path"""
    for root in ALLOWED_ROOTS:
        try:
            full_path.relative_to(root)
            return root
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="Path not under any allowed root")

# Helper function to get virtual path relative to its root
def _get_virtual_path(full_path: Path) -> str:
    """Get path relative to its containing root directory"""
    current_root = _get_current_root(full_path)
    return str(full_path.relative_to(current_root))

def list_items(path: str) -> List[Dict[str, Any]]:
    full_path = resolve_safe_path(path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    current_root = _get_current_root(full_path)
    items = []
    
    for item in full_path.iterdir():
        is_dir = item.is_dir()
        stat = item.stat()
        
        try:
            # Get path relative to the current root
            rel_path = item.relative_to(current_root)
        except ValueError:
            # Fallback if path resolution fails unexpectedly
            rel_path = item.name

        items.append({
            "name": item.name,
            "path": str(rel_path),
            "type": "folder" if is_dir else "file",
            "size": stat.st_size if not is_dir else None,
            "modified": stat.st_mtime,
        })
    
    # Sort: folders first, then by name (case-insensitive)
    return sorted(items, key=lambda x: (x["type"] != "folder", x["name"].lower()))


def create_folder(path: str) -> str:
    full_path = resolve_safe_path(path)
    if full_path.exists():
        raise HTTPException(status_code=409, detail="Folder already exists")
    full_path.mkdir(parents=True, exist_ok=False)
    return _get_virtual_path(full_path)


def rename_item(path: str, new_name: str) -> str:
    old_path = resolve_safe_path(path)
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="Item not found")
    
    new_path = old_path.parent / new_name
    if new_path.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")
    
    old_path.rename(new_path)
    return _get_virtual_path(new_path)


def delete_item(path: str) -> None:
    full_path = resolve_safe_path(path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Item not found")
    if full_path.is_file():
        full_path.unlink()
    else:
        shutil.rmtree(full_path)


def upload_file(path: str, filename: str, content: bytes) -> Dict[str, Any]:
    dir_path = resolve_safe_path(path)
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="Upload path must be a directory")
    
    file_path = dir_path / filename
    if file_path.exists():
        raise HTTPException(status_code=409, detail="File already exists")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    return {
        "file_path": _get_virtual_path(file_path),
        "size": file_path.stat().st_size
    }


def upload_and_extract_zip(path: str, zip_content: bytes, zip_filename: str) -> str:
    if not zip_filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files allowed")
    
    dir_path = resolve_safe_path(path)
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="Target must be a directory")
    
    extract_to = dir_path / Path(zip_filename).stem
    if extract_to.exists():
        raise HTTPException(status_code=409, detail="Folder already exists")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "upload.zip"
        zip_path.write_bytes(zip_content)
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Security check: Prevent Zip Slip vulnerability
            for member in zf.infolist():
                member_path = (extract_to / member.filename).resolve()
                if not str(member_path).startswith(str(extract_to.resolve())):
                    raise HTTPException(status_code=400, detail="Invalid zip file: contains path traversal")
            zf.extractall(extract_to)
    
    return _get_virtual_path(extract_to)


def download_file_path(path: str) -> Path:
    file_path = resolve_safe_path(path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file_path


def get_folder_zip_generator(path: str) -> tuple[str, Generator[bytes, None, None]]:
    folder_path = resolve_safe_path(path)
    if not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")
    zip_filename = f"{folder_path.name}.zip"
    return zip_filename, generate_zip_from_folder(folder_path)


def copy_item(src_path: str, dest_path: str) -> str:
    src = resolve_safe_path(src_path)
    dst_dir = resolve_safe_path(dest_path)
    
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if not dst_dir.is_dir():
        raise HTTPException(status_code=400, detail="Destination must be a directory")
    
    dst = dst_dir / src.name
    if dst.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")
    
    if src.is_file():
        shutil.copy2(src, dst)
    else:
        shutil.copytree(src, dst)
    
    return _get_virtual_path(dst)


def move_item(src_path: str, dest_path: str) -> str:
    src = resolve_safe_path(src_path)
    dst_dir = resolve_safe_path(dest_path)
    
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if not dst_dir.is_dir():
        raise HTTPException(status_code=400, detail="Destination must be a directory")
    
    dst = dst_dir / src.name
    if dst.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")
    
    shutil.move(str(src), str(dst))
    return _get_virtual_path(dst)
