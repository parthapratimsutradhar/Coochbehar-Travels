import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import FinancialAccountOwnerType, FinancialAccountType
from app.core.messages.error import FinancialAccountError
from app.core.messages.success import FinancialAccountSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.financial import FinancialAccountCreate, FinancialAccountResponse, FinancialAccountUpdate
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.services.financial_account_service import FinancialAccountService

router = APIRouter(
    prefix="/admin/financial-accounts",
    tags=["Admin - Financial Accounts"],
)


def _raise_financial_account_error(exc: ValueError) -> None:
    message = str(exc)
    if "already" in message.lower() or "exists" in message.lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    if "required" in message.lower() or "does not match" in message.lower():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a financial account",
)
def create_financial_account(
    payload: FinancialAccountCreate,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> ActionResponse:
    del current_user
    try:
        FinancialAccountService(db).create_account(payload)
    except ValueError as exc:
        _raise_financial_account_error(exc)
    return ActionResponse(message=FinancialAccountSuccess.CREATED)


@router.get(
    "",
    response_model=PaginatedResponse[FinancialAccountResponse],
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List all financial accounts",
)
def list_financial_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    owner_type: FinancialAccountOwnerType | None = Query(None),
    account_type: FinancialAccountType | None = Query(None),
    owner_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> PaginatedResponse[FinancialAccountResponse]:
    del current_user
    items, total_items = FinancialAccountService(db).list_accounts(
        page=page,
        page_size=page_size,
        owner_type=owner_type,
        account_type=account_type,
        owner_id=owner_id,
        is_active=is_active,
        search=search,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return PaginatedResponse[
        FinancialAccountResponse
    ](
        message=FinancialAccountSuccess.RETRIEVED,
        data=[FinancialAccountResponse.model_validate(item) for item in items],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.get(
    "/customer-vendor",
    response_model=PaginatedResponse[FinancialAccountResponse],
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List customer/vendor financial accounts by account type",
)
def list_customer_vendor_financial_accounts(
    owner_type: FinancialAccountOwnerType = Query(..., description="Filter by CUSTOMER or VENDOR"),
    account_type: FinancialAccountType | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> PaginatedResponse[FinancialAccountResponse]:
    del current_user
    if owner_type not in (FinancialAccountOwnerType.CUSTOMER, FinancialAccountOwnerType.VENDOR):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="owner_type must be CUSTOMER or VENDOR.")

    items, total_items = FinancialAccountService(db).list_accounts(
        page=page,
        page_size=page_size,
        owner_type=owner_type,
        account_type=account_type,
        is_active=is_active,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return PaginatedResponse[
        FinancialAccountResponse
    ](
        message=FinancialAccountSuccess.RETRIEVED,
        data=[FinancialAccountResponse.model_validate(item) for item in items],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.patch(
    "/{account_id}",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update a financial account",
)
def update_financial_account(
    account_id: uuid.UUID,
    payload: FinancialAccountUpdate,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> ActionResponse:
    del current_user
    try:
        FinancialAccountService(db).update_account(account_id, payload)
    except ValueError as exc:
        message = str(exc)
        if message == FinancialAccountError.ACCOUNT_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        _raise_financial_account_error(exc)
    return ActionResponse(message=FinancialAccountSuccess.UPDATED)


@router.patch(
    "/customer-vendor/{account_id}",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update a customer/vendor financial account",
)
def update_customer_vendor_financial_account(
    account_id: uuid.UUID,
    payload: FinancialAccountUpdate,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> ActionResponse:
    del current_user
    try:
        account = FinancialAccountService(db).get_account(account_id)
    except ValueError as exc:
        if str(exc) == FinancialAccountError.ACCOUNT_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if account.owner_type not in (FinancialAccountOwnerType.CUSTOMER, FinancialAccountOwnerType.VENDOR):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="This endpoint only supports customer/vendor financial accounts.")

    try:
        FinancialAccountService(db).update_account(account_id, payload)
    except ValueError as exc:
        message = str(exc)
        if message == FinancialAccountError.ACCOUNT_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        _raise_financial_account_error(exc)
    return ActionResponse(message=FinancialAccountSuccess.UPDATED)


@router.delete(
    "/{account_id}",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Delete a financial account",
)
def delete_financial_account(
    account_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> ActionResponse:
    del current_user
    try:
        FinancialAccountService(db).delete_account(account_id)
    except ValueError as exc:
        message = str(exc)
        if message == FinancialAccountError.ACCOUNT_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        _raise_financial_account_error(exc)
    return ActionResponse(message=FinancialAccountSuccess.DELETED)


@router.delete(
    "/customer-vendor/{account_id}",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Delete a customer/vendor financial account",
)
def delete_customer_vendor_financial_account(
    account_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
) -> ActionResponse:
    del current_user
    try:
        account = FinancialAccountService(db).get_account(account_id)
    except ValueError as exc:
        if str(exc) == FinancialAccountError.ACCOUNT_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if account.owner_type not in (FinancialAccountOwnerType.CUSTOMER, FinancialAccountOwnerType.VENDOR):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="This endpoint only supports customer/vendor financial accounts.")

    try:
        FinancialAccountService(db).delete_account(account_id)
    except ValueError as exc:
        message = str(exc)
        if message == FinancialAccountError.ACCOUNT_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        _raise_financial_account_error(exc)
    return ActionResponse(message=FinancialAccountSuccess.DELETED)
