import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.db.database import get_db
from app.models.account import Account
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.expense_service import ExpenseService

router = APIRouter(
    prefix="/admin/expenses",
    tags=["Admin - Expenses"],
)


@router.post(
    "",
    response_model=SuccessResponse[ExpenseResponse],
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Record a new expense",
)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = ExpenseService(db)
    expense = service.create_expense(payload, staff_user=current_user)
    return SuccessResponse(
        message="Expense recorded successfully",
        data=ExpenseResponse.model_validate(expense),
    )


@router.get(
    "",
    response_model=PaginatedResponse[ExpenseResponse],
    summary="List expenses (Admin)",
)
def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None, ge=2000),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = ExpenseService(db)
    result = service.list_expenses(page=page, page_size=page_size, category=category, month=month, year=year)
    return PaginatedResponse(
        message="Expenses fetched successfully",
        data=[ExpenseResponse.model_validate(e) for e in result["items"]],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.get(
    "/{expense_id}",
    response_model=SuccessResponse[ExpenseResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Get expense detail",
)
def get_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = ExpenseService(db)
    expense = service.get_expense(expense_id)
    return SuccessResponse(
        message="Expense fetched successfully",
        data=ExpenseResponse.model_validate(expense),
    )


@router.patch(
    "/{expense_id}",
    response_model=SuccessResponse[ExpenseResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Update an expense",
)
def update_expense(
    expense_id: uuid.UUID,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = ExpenseService(db)
    expense = service.update_expense(expense_id, payload)
    return SuccessResponse(
        message="Expense updated successfully",
        data=ExpenseResponse.model_validate(expense),
    )


@router.delete(
    "/{expense_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Soft-delete an expense",
)
def delete_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = ExpenseService(db)
    service.delete_expense(expense_id)
    return ActionResponse(message="Expense deleted successfully")
