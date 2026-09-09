from decimal import Decimal
import uuid
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session
from app.models.expense import Expense


class ExpenseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, expense_id: uuid.UUID) -> Expense | None:
        stmt = select(Expense).where(Expense.id == expense_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, **kwargs) -> Expense:
        expense = Expense(**kwargs)
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def list_expenses(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        month: int | None = None,
        year: int | None = None,
    ) -> tuple[list[Expense], int]:
        stmt = select(Expense).where(Expense.is_active.is_(True))
        if category:
            stmt = stmt.where(Expense.expense_category.ilike(category))
        if month:
            stmt = stmt.where(extract("month", Expense.date) == month)
        if year:
            stmt = stmt.where(extract("year", Expense.date) == year)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        expenses = self.db.execute(
            stmt.order_by(Expense.date.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(expenses), total

    def update(self, expense: Expense, update_data: dict) -> Expense:
        for k, v in update_data.items():
            if v is not None:
                setattr(expense, k, v)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, expense: Expense) -> None:
        expense.is_active = False
        self.db.commit()
        self.db.refresh(expense)

    def get_total_expenses(self, month: int | None = None, year: int | None = None) -> Decimal:
        stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.is_active.is_(True))
        if month:
            stmt = stmt.where(extract("month", Expense.date) == month)
        if year:
            stmt = stmt.where(extract("year", Expense.date) == year)
        return Decimal(self.db.execute(stmt).scalar_one())
