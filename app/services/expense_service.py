import uuid
from fastapi import HTTPException, status
from sqlalchemy import extract
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.financial_transaction import FinancialTransaction
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.financial_service import FinancialService


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_expense(self, payload: ExpenseCreate, staff_user: Account) -> FinancialTransaction:
        return FinancialService(self.db).record_expense(
            amount=payload.amount,
            currency="INR",
            payment_method=payload.payment_method,
            category=payload.expense_category,
            description=payload.description,
            vendor_id=payload.vendor_id,
            reference=payload.reference,
            attachments=payload.attachments,
            created_by_account_id=staff_user.id,
            transaction_date=payload.date,
        )

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
            FinancialTransaction.status == "POSTED",
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

    def update_expense(self, expense_id: uuid.UUID, payload: ExpenseUpdate) -> FinancialTransaction:
        self.get_expense(expense_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Posted expenses cannot be edited; create a correcting transaction instead.",
        )

    def delete_expense(self, expense_id: uuid.UUID) -> None:
        self.get_expense(expense_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Posted expenses cannot be deleted; create a correcting transaction instead.",
        )
