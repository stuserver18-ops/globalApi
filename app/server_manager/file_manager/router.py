from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from .schemas import RenamePayload, MoveCopyPayload
from .service import (
    list_items, create_folder, rename_item, delete_item,
    upload_file, upload_and_extract_zip,
    download_file_path, get_folder_zip_generator,
    copy_item, move_item
)
from utils.router_logger import get_router_logger
import logging

router = APIRouter()
logger = get_router_logger("fileManager")


# -----------------------
# Routes with simplified error handling
# -----------------------

@router.get("/list")
async def api_list_files(path: str = ""):
    try:
        items = list_items(path)
        return {"items": items}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_list_files: {e}", exc_info=True)
        raise


@router.post("/mkdir")
async def api_create_folder(path: str):
    try:
        rel_path = create_folder(path)
        return {"success": True, "path": rel_path}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_create_folder: {e}", exc_info=True)
        raise


@router.post("/rename")
async def api_rename_item(path: str, payload: RenamePayload):
    try:
        new_path = rename_item(path, payload.new_name)
        return {"success": True, "new_path": new_path}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_rename_item: {e}", exc_info=True)
        raise


@router.delete("/delete")
async def api_delete_item(path: str):
    try:
        delete_item(path)
        return {"success": True}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_delete_item: {e}", exc_info=True)
        raise


@router.post("/upload/file")
async def api_upload_file(path: str = "", file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename or "uploaded_file"
        result = upload_file(path, filename, content)
        return {"success": True, **result}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_upload_file: {e}", exc_info=True)
        raise


@router.post("/upload/folder")
async def api_upload_folder_as_zip(path: str = "", zip_file: UploadFile = File(...)):
    try:
        content = await zip_file.read()
        filename = zip_file.filename or "uploaded.zip"
        folder_path = upload_and_extract_zip(path, content, filename)
        return {"success": True, "folder_path": folder_path}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_upload_folder_as_zip: {e}", exc_info=True)
        raise


@router.get("/download/file")
async def api_download_file(path: str):
    try:
        file_path = download_file_path(path)
        return FileResponse(file_path, filename=file_path.name)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_download_file: {e}", exc_info=True)
        raise


@router.get("/download/folder")
async def api_download_folder_as_zip(path: str):
    try:
        zip_filename, generator = get_folder_zip_generator(path)
        return StreamingResponse(
            generator,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_download_folder_as_zip: {e}", exc_info=True)
        raise


@router.post("/copy")
async def api_copy_item(path: str, payload: MoveCopyPayload):
    try:
        dest = copy_item(path, payload.destination)
        return {"success": True, "destination": dest}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_copy_item: {e}", exc_info=True)
        raise


@router.post("/move")
async def api_move_item(path: str, payload: MoveCopyPayload):
    try:
        dest = move_item(path, payload.destination)
        return {"success": True, "destination": dest}
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error in api_move_item: {e}", exc_info=True)
        raise
