import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.expense import Expense
from app.repository.expense_repo import ExpenseRepository
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ExpenseRepository(db)

    def create_expense(self, payload: ExpenseCreate, staff_user: Account) -> Expense:
        data = payload.model_dump()
        data["created_by_account_id"] = staff_user.id
        return self.repo.create(**data)

    def get_expense(self, expense_id: uuid.UUID) -> Expense:
        exp = self.repo.get_by_id(expense_id)
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
        items, total = self.repo.list_expenses(
            page=page, page_size=page_size, category=category, month=month, year=year
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def update_expense(self, expense_id: uuid.UUID, payload: ExpenseUpdate) -> Expense:
        expense = self.get_expense(expense_id)
        return self.repo.update(expense, payload.model_dump(exclude_unset=True))

    def delete_expense(self, expense_id: uuid.UUID) -> None:
        expense = self.get_expense(expense_id)
        self.repo.delete(expense)
