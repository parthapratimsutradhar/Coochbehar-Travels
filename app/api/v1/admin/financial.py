import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only, get_current_admin_or_staff
from app.db.database import get_db
from app.models.account import Account
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.audit_log import AuditLog
from app.schemas.financial import FinancialAccountCreate, FinancialAccountResponse
from app.schemas.financial_operations import FinancialReversalCreate, VendorPaymentCreate
from app.schemas.financial_reports import FinancialDashboardResponse, FinancialReportResponse
from app.schemas.response import SuccessResponse
from app.schemas.wallet import WalletAdjustmentCreate, WalletRefundCreate, WalletResponse, WalletTransactionResponse
from app.services.wallet_service import WalletService
from app.services.financial_service import FinancialService
from app.services.financial_reporting_service import FinancialReportingService

router = APIRouter(prefix="/admin/financial", tags=["Admin - Financial"])


@router.get("/dashboard", response_model=SuccessResponse[FinancialDashboardResponse], summary="Get financial dashboard")
def get_financial_dashboard(
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    del current_user
    return SuccessResponse(message="Financial dashboard fetched successfully", data=FinancialReportingService(db).dashboard())


@router.get("/reports/{report_type}", response_model=SuccessResponse[FinancialReportResponse], summary="Run a financial report")
def get_financial_report(
    report_type: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    del current_user
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date.")
    report = FinancialReportingService(db).report(report_type, start=start_date, end=end_date)
    return SuccessResponse(message="Financial report generated successfully", data=report)


@router.post("/vendor-payments", response_model=SuccessResponse[dict], status_code=status.HTTP_201_CREATED, summary="Record a vendor payment")
def create_vendor_payment(
    payload: VendorPaymentCreate,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    transaction = FinancialService(db).record_vendor_payment(
        amount=payload.amount,
        vendor_id=payload.vendor_id,
        booking_id=payload.booking_id,
        cost_id=payload.cost_id,
        currency="INR",
        payment_method=payload.payment_method,
        reference=payload.reference,
        description=payload.description,
        recorded_by_account_id=current_user.id,
        transaction_date=payload.paid_at,
    )
    return SuccessResponse(message="Vendor payment recorded successfully", data={"id": transaction.id, "transaction_code": transaction.transaction_code, "amount": transaction.amount})


@router.post("/transactions/{transaction_id}/reverse", response_model=SuccessResponse[dict], summary="Reverse a posted financial transaction")
def reverse_financial_transaction(
    transaction_id: uuid.UUID,
    payload: FinancialReversalCreate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    reversal = FinancialService(db).reverse_transaction(transaction_id=transaction_id, actor_id=current_user.id, reason=payload.reason)
    return SuccessResponse(message="Financial transaction reversed successfully", data={"id": reversal.id, "transaction_code": reversal.transaction_code, "amount": reversal.amount})


@router.get("/audit", response_model=SuccessResponse[list[dict]], summary="List financial audit activity")
def list_financial_audit(
    limit: int = Query(100, ge=1, le=500),
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    logs = db.query(AuditLog).filter(
        AuditLog.entity_type.in_(["FinancialTransaction", "FinancialAccount"])
    ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return SuccessResponse(message="Financial audit activity fetched successfully", data=[{
        "id": log.id, "account_id": log.account_id, "action": log.action,
        "entity_type": log.entity_type, "entity_id": log.entity_id,
        "old_values": log.old_values, "new_values": log.new_values,
        "created_at": log.created_at,
    } for log in logs])


@router.get("/accounts", response_model=SuccessResponse[list[FinancialAccountResponse]], summary="List financial accounts")
def list_financial_accounts(
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    del current_user
    accounts = db.query(FinancialAccount).order_by(FinancialAccount.account_code).all()
    return SuccessResponse(message="Financial accounts fetched successfully", data=accounts)


@router.post(
    "/accounts",
    response_model=SuccessResponse[FinancialAccountResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a financial account",
)
def create_financial_account(
    payload: FinancialAccountCreate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    if payload.owner_type.value == "CUSTOMER" and payload.owner_id is None:
        raise HTTPException(status_code=422, detail="Customer-owned accounts require an owner_id.")
    account = FinancialAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    db.add(AuditLog(
        account_id=current_user.id,
        action="FINANCIAL_ACCOUNT_CREATED",
        entity_type="FinancialAccount",
        entity_id=account.id,
        new_values={"account_code": account.account_code, "account_type": account.account_type.value},
    ))
    db.commit()
    return SuccessResponse(message="Financial account created successfully", data=account)


@router.patch(
    "/accounts/{account_id}/status",
    response_model=SuccessResponse[FinancialAccountResponse],
    summary="Activate or deactivate a financial account",
)
def update_financial_account_status(
    account_id: uuid.UUID,
    is_active: bool,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    account = db.query(FinancialAccount).filter(FinancialAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Financial account not found.")
    account.is_active = is_active
    db.commit()
    db.refresh(account)
    db.add(AuditLog(
        account_id=current_user.id,
        action="FINANCIAL_ACCOUNT_STATUS_CHANGED",
        entity_type="FinancialAccount",
        entity_id=account.id,
        new_values={"is_active": is_active},
    ))
    db.commit()
    return SuccessResponse(message="Financial account status updated successfully", data=account)


@router.get(
    "/customers/{customer_id}/wallet",
    response_model=SuccessResponse[WalletResponse],
    summary="View a customer wallet",
)
def get_customer_wallet(
    customer_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    del current_user
    service = WalletService(db)
    wallet = service.get_wallet_account(customer_id)
    transactions = service.history(customer_id)
    return SuccessResponse(
        message="Customer wallet fetched successfully",
        data=WalletResponse(
            account_id=wallet.id,
            customer_id=customer_id,
            balance=service.balance(wallet),
            currency=wallet.currency,
            transactions=[WalletTransactionResponse.model_validate(item) for item in transactions],
        ),
    )


@router.post(
    "/customers/{customer_id}/wallet/adjustments",
    response_model=SuccessResponse[WalletTransactionResponse],
    summary="Make an audited customer wallet adjustment",
)
def adjust_customer_wallet(
    customer_id: uuid.UUID,
    payload: WalletAdjustmentCreate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    transaction = WalletService(db).adjust(
        customer_id=customer_id,
        amount=payload.amount,
        direction=payload.direction,
        reason=payload.reason,
        actor=current_user,
        reference=payload.reference,
    )
    return SuccessResponse(
        message="Wallet adjustment recorded successfully",
        data=WalletTransactionResponse.model_validate(transaction),
    )


@router.post(
    "/customers/{customer_id}/wallet/refunds",
    response_model=SuccessResponse[WalletTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Credit a policy-approved refund to a customer wallet",
)
def refund_customer_wallet(
    customer_id: uuid.UUID,
    payload: WalletRefundCreate,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    transaction = WalletService(db).refund_to_wallet(
        customer_id=customer_id,
        amount=payload.amount,
        booking_id=payload.booking_id,
        reason=payload.reason,
        reference=payload.reference,
        actor=current_user,
    )
    return SuccessResponse(
        message="Wallet refund credited successfully",
        data=WalletTransactionResponse.model_validate(transaction),
    )
