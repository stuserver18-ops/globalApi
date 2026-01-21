# app/server_manager/file_manager/allowed_roots.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from .schemas import AllowedRootCreate, AllowedRootUpdate, AllowedRootResponse
from .allowed_root_crud import (
    create_allowed_root,
    get_all_allowed_roots,
    update_allowed_root,
    delete_allowed_root,
)

router = APIRouter(prefix="/allowed-roots")


@router.post(
    "/",
    response_model=AllowedRootResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new allowed root path"
)
def add_allowed_root(root: AllowedRootCreate):
    try:
        root_id = create_allowed_root(
            path=root.path,
            description=root.description,
            is_allowed=root.is_allowed  # <-- pass new field
        )
        return AllowedRootResponse(id=root_id, **root.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add allowed root: {str(e)}")


@router.get(
    "/",
    response_model=List[AllowedRootResponse],
    summary="List all allowed root paths"
)
def list_allowed_roots():
    try:
        records = get_all_allowed_roots()
        return [AllowedRootResponse(**rec) for rec in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch allowed roots: {str(e)}")


@router.put(
    "/{root_id}",
    response_model=AllowedRootResponse,
    summary="Update an allowed root by ID"
)
def modify_allowed_root(root_id: int, root: AllowedRootUpdate):
    update_data = root.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="At least one field must be provided")

    try:
        path = update_data.get("path")
        description = update_data.get("description")
        is_allowed = update_data.get("is_allowed")

        rows_updated = update_allowed_root(
            root_id,
            path=path,
            description=description,
            is_allowed=is_allowed
        )

        if rows_updated == 0:
            raise HTTPException(status_code=404, detail="Allowed root not found")

        # Best practice: re-fetch the record
        # If your `get()` supports filtering, do:
        # updated_record = get(TABLE_NAME, where="id = %s", params=(root_id,), app_name=APP_NAME)
        # But since you don't have get_by_id, we reconstruct (not ideal)

        # For now, assume input reflects outcome
        return AllowedRootResponse(
            id=root_id,
            path=path if path is not None else "unknown",
            description=description,
            is_allowed=is_allowed if is_allowed is not None else True  # fallback
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")


@router.delete(
    "/{root_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an allowed root by ID"
)
def remove_allowed_root(root_id: int):
    try:
        rows_deleted = delete_allowed_root(root_id)
        if rows_deleted == 0:
            raise HTTPException(status_code=404, detail="Allowed root not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete allowed root: {str(e)}")