import uuid
from fastapi import HTTPException, status
from sqlalchemy import extract
from sqlalchemy.orm import Session
from app.core.enums import FinancialTransactionStatus
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.financial_transaction import FinancialTransaction
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.financial_service import FinancialService


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_expense(self, payload: ExpenseCreate, staff_user: Account) -> FinancialTransaction:
        transaction = FinancialService(self.db).record_expense(
            amount=payload.amount,
            currency="INR",
            payment_method=payload.payment_method,
            category=payload.expense_category,
            description=payload.description,
            vendor_id=payload.vendor_id,
            reference=payload.reference,
            attachments=payload.attachments,
            financial_account_id=payload.financial_account_id,
            created_by_account_id=staff_user.id,
            transaction_date=payload.date,
        )
        self.db.add(AuditLog(
            account_id=staff_user.id,
            action="EXPENSE_CREATED",
            entity_type="FinancialTransaction",
            entity_id=transaction.id,
            new_values={"amount": str(transaction.amount), "category": transaction.category},
        ))
        self.db.commit()
        return transaction

    def get_expense(self, expense_id: uuid.UUID) -> FinancialTransaction:
        exp = self.db.query(FinancialTransaction).filter(
            FinancialTransaction.id == expense_id,
            FinancialTransaction.transaction_type == "EXPENSE",
        ).one_or_none()
        if not exp or not exp.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found.")
        return exp

    def list_expenses(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        month: int | None = None,
        year: int | None = None,
    ) -> dict:
        query = self.db.query(FinancialTransaction).filter(
            FinancialTransaction.transaction_type == "EXPENSE",
            FinancialTransaction.status == FinancialTransactionStatus.COMPLETED,
        )
        if category:
            query = query.filter(FinancialTransaction.category.ilike(category))
        if month:
            query = query.filter(extract("month", FinancialTransaction.transaction_date) == month)
        if year:
            query = query.filter(extract("year", FinancialTransaction.transaction_date) == year)
        total = query.count()
        items = query.order_by(FinancialTransaction.transaction_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def update_expense(self, expense_id: uuid.UUID, payload: ExpenseUpdate, staff_user: Account) -> FinancialTransaction:
        existing = self.get_expense(expense_id)
        data = {
            "amount": payload.amount if payload.amount is not None else existing.amount,
            "description": payload.description if payload.description is not None else existing.description,
            "date": payload.date if payload.date is not None else existing.transaction_date,
            "expense_category": payload.expense_category if payload.expense_category is not None else existing.category,
            "payment_method": payload.payment_method if payload.payment_method is not None else existing.payment_method,
            "vendor_id": payload.vendor_id if payload.vendor_id is not None else existing.vendor_id,
            "reference": payload.reference if payload.reference is not None else existing.reference,
            "attachments": payload.attachments if payload.attachments is not None else (existing.metadata_ or {}).get("attachments"),
            "financial_account_id": payload.financial_account_id or (existing.metadata_ or {}).get("financial_account_id"),
        }
        FinancialService(self.db).reverse_transaction(
            transaction_id=existing.id,
            actor_id=staff_user.id,
            reason="Expense corrected by update",
        )
        return self.create_expense(ExpenseCreate.model_validate(data), staff_user)

    def delete_expense(self, expense_id: uuid.UUID, staff_user: Account) -> None:
        expense = self.get_expense(expense_id)
        FinancialService(self.db).reverse_transaction(
            transaction_id=expense.id,
            actor_id=staff_user.id,
            reason="Expense reversed by administrator",
        )
