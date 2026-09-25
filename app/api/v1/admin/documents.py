import mimetypes
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.core.enums import DocumentType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.document import (
    AdminDocumentResponse,
    AdminDocumentUploadRequest,
    BulkDeleteDocumentsRequest,
    DocumentUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.admin_document_service import AdminDocumentService


router = APIRouter(prefix="/admin/documents", tags=["Admin - Documents"])


@router.get(
    "",
    response_model=PaginatedResponse[AdminDocumentResponse], 
    responses={401: {"model": ErrorResponse}}
)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    document_type: DocumentType | None = Query(None),
    document_status: Literal["active", "deleted", "all"] = Query("active", alias="status"),
    customer_id: uuid.UUID | None = Query(None),
    uploaded_by: Literal["CUSTOMER", "ADMIN"] | None = Query(None),
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminDocumentResponse]:
    result = AdminDocumentService(db).list_documents(
        current_user=current_user, page=page, page_size=page_size,
        from_date=from_date, to_date=to_date,
        document_type=document_type, document_status=document_status,
        customer_id=customer_id, uploaded_by=uploaded_by,
    )
    total_pages = result["total_pages"]
    return PaginatedResponse(
        message="Items fetched successfully", data=result["items"],
        pagination=PaginationMeta(
            current_page=page, page_size=page_size, total_items=result["total_items"],
            total_pages=total_pages, has_next=page < total_pages, has_previous=page > 1,
        ),
    )


@router.delete(
    "/bulk", 
    response_model=ActionResponse
)
def bulk_delete_documents(
    payload: BulkDeleteDocumentsRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
) -> ActionResponse:
    count = AdminDocumentService(db).bulk_delete(payload.document_ids, current_user)
    return ActionResponse(message=f"{count} document(s) deleted successfully")


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Upload a customer document",
)
async def upload_customer_document(
    payload: AdminDocumentUploadRequest,
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ActionResponse:
    data = {
        "document_type": payload.document_type,
        "title": payload.title.strip(),
        "description": payload.description.strip() if payload.description else None,
    }
    if not (
        payload.file.startswith("http://")
        or payload.file.startswith("https://")
        or "temporary-uploads" in payload.file
    ):
        raise HTTPException(status_code=422, detail="file must reference a temporary upload")

    mime_type = mimetypes.guess_type(payload.file_name)[0] or "application/octet-stream"
    await AdminDocumentService(db).upload_from_url(
        customer_id=payload.customer_id,
        url_or_id=payload.file,
        current_user=current_user,
        file_name=payload.file_name,
        mime_type=mime_type,
        **data,
    )
    return ActionResponse(message="Document uploaded successfully")


@router.patch(
    "/{document_id}", 
    response_model=ActionResponse, 
    responses={404: {"model": ErrorResponse}}
)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
) -> ActionResponse:
    AdminDocumentService(db).update(document_id, payload)
    return ActionResponse(message="Document updated successfully")
