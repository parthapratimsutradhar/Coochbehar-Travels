import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AccountRole, FinancialAccountOwnerType, FinancialAccountType
from app.models.account import Account
from app.models.financial_account import FinancialAccount
from app.models.vendor import Vendor


class FinancialAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, account_id: uuid.UUID) -> FinancialAccount | None:
        return self.db.get(FinancialAccount, account_id)

    def get_by_account_code(self, account_code: str) -> FinancialAccount | None:
        return self.db.query(FinancialAccount).filter(FinancialAccount.account_code == account_code).one_or_none()

    def exists_for_owner(
        self,
        owner_type: FinancialAccountOwnerType,
        owner_id: uuid.UUID,
        account_type: FinancialAccountType,
    ) -> bool:
        return (
            self.db.query(FinancialAccount)
            .filter(
                FinancialAccount.owner_type == owner_type,
                FinancialAccount.owner_id == owner_id,
                FinancialAccount.account_type == account_type,
            )
            .first()
            is not None
        )

    def validate_owner(self, owner_type: FinancialAccountOwnerType | None, owner_id: uuid.UUID | None) -> None:
        if owner_type in (FinancialAccountOwnerType.CUSTOMER, FinancialAccountOwnerType.VENDOR):
            if owner_id is None:
                raise ValueError("owner_id is required for customer/vendor financial accounts.")

            if owner_type == FinancialAccountOwnerType.CUSTOMER:
                owner = self.db.get(Account, owner_id)
                if owner is None or owner.role != AccountRole.CUSTOMER:
                    raise ValueError("The owner_id does not match a valid customer account.")
                return

            owner = self.db.get(Vendor, owner_id)
            if owner is None:
                raise ValueError("The owner_id does not match a valid vendor record.")
            return

    def list_accounts(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        owner_type: FinancialAccountOwnerType | None = None,
        account_type: FinancialAccountType | None = None,
        owner_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[FinancialAccount], int]:
        stmt = select(FinancialAccount)
        if owner_type is not None:
            stmt = stmt.where(FinancialAccount.owner_type == owner_type)
        if account_type is not None:
            stmt = stmt.where(FinancialAccount.account_type == account_type)
        if owner_id is not None:
            stmt = stmt.where(FinancialAccount.owner_id == owner_id)
        if is_active is not None:
            stmt = stmt.where(FinancialAccount.is_active.is_(is_active))
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                FinancialAccount.account_code.ilike(term)
                | FinancialAccount.name.ilike(term)
            )

        stmt = stmt.order_by(FinancialAccount.created_at.desc())
        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return list(rows), total_items

    def create(self, data: dict) -> FinancialAccount:
        account = FinancialAccount(**data)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, account: FinancialAccount, update_data: dict) -> FinancialAccount:
        for field, value in update_data.items():
            if value is not None and hasattr(account, field):
                setattr(account, field, value)
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, account: FinancialAccount) -> FinancialAccount:
        account.is_active = False
        self.db.commit()
        self.db.refresh(account)
        return account
