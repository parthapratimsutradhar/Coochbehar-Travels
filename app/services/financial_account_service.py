import uuid

from app.core.enums import FinancialAccountOwnerType, FinancialAccountType
from app.core.messages.error import FinancialAccountError
from app.repository.financial_account_repo import FinancialAccountRepository
from app.schemas.financial import FinancialAccountCreate, FinancialAccountUpdate


class FinancialAccountService:
    def __init__(self, db):
        self.db = db
        self.repo = FinancialAccountRepository(db)

    def create_account(self, payload: FinancialAccountCreate):
        data = payload.model_dump(exclude_unset=True)
        owner_type = data.get("owner_type")
        if owner_type == FinancialAccountOwnerType.CUSTOMER:
            raise ValueError("Customer financial accounts are not supported in this system. Customers use wallet accounts instead.")

        self.repo.validate_owner(owner_type, data.get("owner_id"))

        if self.repo.get_by_account_code(data["account_code"]):
            raise ValueError(FinancialAccountError.ACCOUNT_CODE_EXISTS)

        owner_id = data.get("owner_id")
        account_type = data.get("account_type")
        if owner_type == FinancialAccountOwnerType.VENDOR:
            if owner_id is None:
                raise ValueError(FinancialAccountError.OWNER_REQUIRED)
            if account_type is None:
                raise ValueError("account_type is required for vendor financial accounts.")
            if self.repo.exists_for_owner(owner_type, owner_id, account_type):
                raise ValueError(FinancialAccountError.DUPLICATE_OWNER_ACCOUNT)

        return self.repo.create(data)

    def get_account(self, account_id: uuid.UUID):
        account = self.repo.get_by_id(account_id)
        if account is None:
            raise ValueError(FinancialAccountError.ACCOUNT_NOT_FOUND)
        return account

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
    ) -> tuple[list, int]:
        if owner_type == FinancialAccountOwnerType.CUSTOMER:
            raise ValueError("Customer financial accounts are not supported in this system. Customers use wallet accounts instead.")
        return self.repo.list_accounts(
            page=page,
            page_size=page_size,
            owner_type=owner_type,
            account_type=account_type,
            owner_id=owner_id,
            is_active=is_active,
            search=search,
        )

    def update_account(self, account_id: uuid.UUID, payload: FinancialAccountUpdate):
        account = self.get_account(account_id)
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return account

        owner_type = data.get("owner_type", account.owner_type)
        owner_id = data.get("owner_id", account.owner_id)
        account_type = data.get("account_type", account.account_type)

        if owner_type == FinancialAccountOwnerType.CUSTOMER or account.owner_type == FinancialAccountOwnerType.CUSTOMER:
            raise ValueError("Customer financial accounts are not supported in this system. Customers use wallet accounts instead.")

        self.repo.validate_owner(owner_type, owner_id)

        if "account_code" in data and data["account_code"] != account.account_code:
            existing = self.repo.get_by_account_code(data["account_code"])
            if existing is not None and existing.id != account.id:
                raise ValueError(FinancialAccountError.ACCOUNT_CODE_EXISTS)

        if owner_type == FinancialAccountOwnerType.VENDOR:
            if owner_id is None:
                raise ValueError(FinancialAccountError.OWNER_REQUIRED)
            if self.repo.exists_for_owner(owner_type, owner_id, account_type) and (
                account.owner_type != owner_type or account.owner_id != owner_id or account.account_type != account_type
            ):
                raise ValueError(FinancialAccountError.DUPLICATE_OWNER_ACCOUNT)

        return self.repo.update(account, data)

    def delete_account(self, account_id: uuid.UUID):
        account = self.get_account(account_id)
        return self.repo.delete(account)
