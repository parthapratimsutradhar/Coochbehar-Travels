import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.db.database import get_db
from app.models.account import Account
from app.schemas.financial_transaction import (
    FinancialReportDownloadRequest,
    FinancialTransactionCreate,
    FinancialTransactionResponse,
    FinancialTransactionUpdate,
    financial_transaction_response,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.financial_transaction_service import FinancialTransactionService

router = APIRouter(
    prefix="/admin/financial",
    tags=["Admin - Financial"],
)


@router.post(
    "/transactions",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Create a transaction (income or expense)",
)
def create_transaction(
    payload: FinancialTransactionCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = FinancialTransactionService(db)
    service.create_transaction(payload, current_user)
    return ActionResponse(message="Financial transaction created successfully")


@router.get(
    "/transactions",
    response_model=PaginatedResponse[FinancialTransactionResponse],
    summary="List financial transactions with filters and search",
)
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    booking_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    vendor_id: uuid.UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = FinancialTransactionService(db)
    result = service.list_transactions(
        transaction_type=transaction_type,
        category=category,
        status=status,
        booking_id=booking_id,
        customer_id=customer_id,
        vendor_id=vendor_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        message="Financial transactions fetched successfully",
        data=[financial_transaction_response(item) for item in result["items"]],
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
    "/reports",
    response_model=SuccessResponse[dict],
    summary="Generate financial reports including income, expenses, and referral income",
)
def generate_reports(
    report_type: str = Query(default="income", description="income, expenses, referral_income, all"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = FinancialTransactionService(db)
    report = service.build_report(report_type, start_date=start_date, end_date=end_date)
    return SuccessResponse(message="Financial report generated successfully", data=report)


@router.get(
    "/statistics",
    response_model=SuccessResponse[dict],
    summary="View total income, total expenses, and net profit or loss for a selected period",
)
def financial_statistics(
    period: str = Query(default="monthly", description="daily, weekly, monthly, yearly"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = FinancialTransactionService(db)
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date cannot be after end_date.")
    summary = service.get_summary(start_date=start_date, end_date=end_date)
    period_summary = {
        "period": period,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_income": str(summary["total_income"]),
        "total_expenses": str(summary["total_expenses"]),
        "referral_income": str(summary["referral_income"]),
        "net_profit_loss": str(summary["net_profit_loss"]),
    }
    return SuccessResponse(message="Financial statistics fetched successfully", data=period_summary)


@router.put(
    "/transactions/{transaction_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update an existing financial transaction",
)
def update_transaction(
    transaction_id: uuid.UUID,
    payload: FinancialTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = FinancialTransactionService(db)
    service.update_transaction(transaction_id, payload, current_user)
    return ActionResponse(message="Financial transaction updated successfully")


@router.delete(
    "/transactions/{transaction_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete a financial transaction",
)
def delete_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = FinancialTransactionService(db)
    service.delete_transaction(transaction_id)
    return ActionResponse(message="Financial transaction deleted successfully")


@router.post(
    "/download",
    summary="Download financial reports in CSV, Excel, or PDF",
    response_class=Response,
    responses={
        200: {
            "description": "Generated report file for download.",
            "content": {
                "text/csv": {"schema": {"type": "string", "format": "binary"}},
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                "application/vnd.ms-excel": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
def download_report(
    payload: FinancialReportDownloadRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    report_type = payload.report_type.lower()
    report_format = payload.format.lower()
    period = payload.period.lower()

    start_obj = payload.start_date
    end_obj = payload.end_date

    if start_obj and end_obj and start_obj > end_obj:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date cannot be after end_date.")

    service = FinancialTransactionService(db)
    report = service.build_report(report_type, start_date=start_obj, end_date=end_obj)
    rows = report["rows"]
    filename = f"financial_{report_type}_{period}.{report_format}"

    if report_format == "pdf":
        pdf_bytes = service.export_pdf(rows, report_type)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if report_format == "excel":
        excel_bytes = service.export_excel(rows, report_type)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.ms-excel",
            headers={"Content-Disposition": f'attachment; filename="{filename.rsplit(".", 1)[0] + ".csv"}"'},
        )

    csv_blob = service.export_csv(rows, report_type)
    return Response(
        content=csv_blob,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
