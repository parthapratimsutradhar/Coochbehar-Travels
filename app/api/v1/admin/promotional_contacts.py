from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.db.database import get_db
from app.models.account import Account
from app.models.promonal_contact import PromonalContact
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.promotional_contact import (
    PromotionalContactCreate,
    PromotionalContactImportResult,
    PromotionalContactResponse,
    PromotionalContactUpdate,
)
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.promotional_contact_service import (
    MAX_IMPORT_SIZE,
    PromotionalContactService,
)


router = APIRouter(
    prefix="/admin/promotional-contacts",
    tags=["Admin - Promotional Contacts"],
)


def _get_or_404(service: PromotionalContactService, contact_id: UUID) -> PromonalContact:
    contact = service.get_contact(contact_id)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotional contact not found",
        )
    return contact


@router.get("", response_model=PaginatedResponse[PromotionalContactResponse])
def list_promotional_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    contacts, total_items = PromotionalContactService(db).list_contacts(
        page=page,
        page_size=page_size,
        search=search,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return PaginatedResponse(
        message="Promotional contacts fetched successfully",
        data=contacts,
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[PromotionalContactResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def create_promotional_contact(
    payload: PromotionalContactCreate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    contact = PromotionalContactService(db).create_contact(payload.model_dump())
    return SuccessResponse(message="Promotional contact created successfully", data=contact)


@router.patch(
    "/{contact_id}",
    response_model=SuccessResponse[PromotionalContactResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def update_promotional_contact(
    contact_id: UUID,
    payload: PromotionalContactUpdate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = PromotionalContactService(db)
    contact = _get_or_404(service, contact_id)
    updated = service.update_contact(contact, payload.model_dump(exclude_unset=True))
    return SuccessResponse(message="Promotional contact updated successfully", data=updated)


@router.delete(
    "/{contact_id}",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_promotional_contact(
    contact_id: UUID,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = PromotionalContactService(db)
    service.delete_contact(_get_or_404(service, contact_id))
    return ActionResponse(message="Promotional contact deleted successfully")


@router.get("/export", summary="Export promotional contacts")
def export_promotional_contacts(
    format: Literal["json", "csv", "xlsx"] = "json",
    search: str | None = Query(None),
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    content, filename, media_type = PromotionalContactService(db).export_contacts(
        format,
        search=search,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/import",
    response_model=SuccessResponse[PromotionalContactImportResult],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Import promotional contacts",
)
async def import_promotional_contacts(
    file: UploadFile = File(...),
    format: Annotated[Literal["json", "csv", "xlsx"], Query()] = "csv",
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    content = await file.read(MAX_IMPORT_SIZE + 1)
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is larger than 25 MB",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import file is empty",
        )
    try:
        imported_count = PromotionalContactService(db).import_contacts(content, format)
    except (ValueError, ValidationError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid import file: {exc}",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Import could not be saved because of a database conflict",
        ) from exc
    return SuccessResponse(
        message="Promotional contacts imported successfully",
        data=PromotionalContactImportResult(imported_count=imported_count),
    )


@router.get("/{contact_id}", response_model=SuccessResponse[PromotionalContactResponse])
def get_promotional_contact(
    contact_id: UUID,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    contact = _get_or_404(PromotionalContactService(db), contact_id)
    return SuccessResponse(
        message="Promotional contact fetched successfully",
        data=contact,
    )
