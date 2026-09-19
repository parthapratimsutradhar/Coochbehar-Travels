import uuid
from datetime import datetime
from decimal import Decimal
from typing import Iterable, TypedDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import (
    FinancialTransactionStatus,
    FinancialTransactionType,
    PaymentMethod,
)
from app.models.audit_log import AuditLog
from app.models.booking_costs import BookingCost
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry


SYSTEM_ACCOUNT_DEFINITIONS = (
    ("1000", "Cash", "ASSET"),
    ("1010", "Bank", "ASSET"),
    ("1020", "Razorpay", "ASSET"),
    ("1100", "Customer Receivable", "ASSET"),
    ("2000", "Vendor Payable", "LIABILITY"),
    ("4000", "Tour Revenue", "REVENUE"),
    ("5000", "Hotel Expense", "EXPENSE"),
    ("5010", "Transport Expense", "EXPENSE"),
    ("5020", "Flight Expense", "EXPENSE"),
    ("5030", "Meal Expense", "EXPENSE"),
    ("5040", "Activity Expense", "EXPENSE"),
    ("5050", "Marketing Expense", "EXPENSE"),
    ("5060", "Other Expense", "EXPENSE"),
    ("6000", "Referral Reward Expense", "EXPENSE"),
    ("6100", "Wallet Adjustments", "EXPENSE"),
)


class LedgerEntry(TypedDict):
    account_id: uuid.UUID
    debit: Decimal
    credit: Decimal
    description: str | None


class FinancialService:
    """Single write boundary for posted double-entry financial transactions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def initialize_system_accounts(self) -> list[FinancialAccount]:
        """Create stable system accounts without duplicating existing accounts."""
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            accounts = []
            for account_code, name, account_type in SYSTEM_ACCOUNT_DEFINITIONS:
                account = (
                    self.db.query(FinancialAccount)
                    .filter_by(account_code=account_code)
                    .one_or_none()
                )
                if account is None:
                    account = FinancialAccount(
                        account_code=account_code,
                        name=name,
                        account_type=account_type,
                    )
                    self.db.add(account)
                    self.db.flush()
                accounts.append(account)
            return accounts

    def create_transaction(
        self,
        *,
        transaction_type: FinancialTransactionType,
        amount: Decimal,
        entries: Iterable[LedgerEntry],
        status_: FinancialTransactionStatus = FinancialTransactionStatus.POSTED,
        external_reference: str | None = None,
        transaction_code: str | None = None,
        transaction_date: datetime | None = None,
        **attributes: object,
    ) -> FinancialTransaction:
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Amount must be positive.")

        normalized_entries = list(entries)
        if not normalized_entries:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least two ledger entries are required.")

        total_debit = sum((Decimal(entry["debit"]) for entry in normalized_entries), Decimal("0"))
        total_credit = sum((Decimal(entry["credit"]) for entry in normalized_entries), Decimal("0"))
        if total_debit != total_credit or total_debit != amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Financial transaction entries must balance to the transaction amount.",
            )

        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            account_ids = {entry["account_id"] for entry in normalized_entries}
            accounts = self.db.query(FinancialAccount).filter(FinancialAccount.id.in_(account_ids)).all()
            if len(accounts) != len(account_ids) or any(not account.is_active for account in accounts):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every ledger account must be active.")

            transaction = FinancialTransaction(
                transaction_code=transaction_code or f"FT-{uuid.uuid4().hex[:20].upper()}",
                transaction_type=transaction_type,
                status=status_,
                amount=amount,
                external_reference=external_reference,
                transaction_date=transaction_date or datetime.utcnow(),
                **attributes,
            )
            self.db.add(transaction)
            self.db.flush()
            self.db.add_all(
                [
                    FinancialTransactionEntry(transaction_id=transaction.id, **entry)
                    for entry in normalized_entries
                ]
            )
            self.db.flush()
            return transaction

    def _system_account(
        self,
        account_code: str,
        name: str,
        account_type: str,
    ) -> FinancialAccount:
        account = self.db.query(FinancialAccount).filter_by(account_code=account_code).one_or_none()
        if account is None:
            account = FinancialAccount(
                account_code=account_code,
                name=name,
                account_type=account_type,
            )
            self.db.add(account)
            self.db.flush()
        return account

    def record_booking_payment(
        self,
        *,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        amount: Decimal,
        currency: str,
        payment_method: object,
        payment_status: object,
        gateway: str | None,
        gateway_transaction_id: str | None,
        external_reference: str | None,
        description: str | None,
        recorded_by_account_id: uuid.UUID | None,
        transaction_date: datetime | None,
    ) -> FinancialTransaction:
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive.")
        if external_reference:
            existing = self.db.query(FinancialTransaction).filter(
                FinancialTransaction.external_reference == external_reference
            ).one_or_none()
            if existing is not None:
                return existing
        if str(payment_status) not in {
            "FinancialTransactionStatus.POSTED",
            "PaymentStatus.SUCCESS",
            "POSTED",
            "SUCCESS",
        }:
            raise HTTPException(
                status_code=422,
                detail="Only successful payments can be posted to the financial ledger.",
            )
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            source = {
                "RAZORPAY": ("1020", "Razorpay"),
                "BANK_TRANSFER": ("1010", "Bank"),
            }.get(getattr(payment_method, "value", payment_method), ("1000", "Cash"))
            source_account = self._system_account(source[0], source[1], "ASSET")
            receivable = self._system_account("1100", "Customer Receivable", "ASSET")
            return self._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.BOOKING_PAYMENT,
                amount=amount,
                entries=[
                    {"account_id": source_account.id, "debit": amount, "credit": Decimal("0"), "description": None},
                    {"account_id": receivable.id, "debit": Decimal("0"), "credit": amount, "description": None},
                ],
                booking_id=booking_id,
                customer_id=customer_id,
                currency=currency,
                payment_method=payment_method,
                gateway=gateway,
                gateway_transaction_id=gateway_transaction_id,
                external_reference=external_reference,
                description=description,
                created_by_account_id=recorded_by_account_id,
                transaction_date=transaction_date,
            )

    def record_expense(
        self,
        *,
        amount: Decimal,
        currency: str,
        payment_method: object,
        category: str,
        description: str | None,
        vendor_id: uuid.UUID | None,
        reference: str | None,
        attachments: list[str] | None,
        financial_account_id: uuid.UUID | None = None,
        created_by_account_id: uuid.UUID,
        transaction_date: datetime | None,
    ) -> FinancialTransaction:
        category_codes = {
            "hotel": ("5000", "Hotel Expense"),
            "transport": ("5010", "Transport Expense"),
            "flight": ("5020", "Flight Expense"),
            "meal": ("5030", "Meal Expense"),
            "activity": ("5040", "Activity Expense"),
            "marketing": ("5050", "Marketing Expense"),
        }
        source_codes = {
            "RAZORPAY": ("1020", "Razorpay"),
            "BANK_TRANSFER": ("1010", "Bank"),
        }
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            expense_code, expense_name = category_codes.get(
                category.lower(), ("5060", "Other Expense")
            )
            source_code, source_name = source_codes.get(
                getattr(payment_method, "value", payment_method), ("1000", "Cash")
            )
            expense_account = self._system_account(expense_code, expense_name, "EXPENSE")
            if financial_account_id is not None:
                expense_account = self.db.query(FinancialAccount).filter(
                    FinancialAccount.id == financial_account_id,
                    FinancialAccount.is_active.is_(True),
                ).one_or_none()
                if expense_account is None:
                    raise HTTPException(status_code=422, detail="Expense financial account is not active or does not exist.")
            source_account = self._system_account(source_code, source_name, "ASSET")
            return self._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.EXPENSE,
                amount=amount,
                entries=[
                    {"account_id": expense_account.id, "debit": amount, "credit": Decimal("0"), "description": description},
                    {"account_id": source_account.id, "debit": Decimal("0"), "credit": amount, "description": description},
                ],
                currency=currency,
                payment_method=payment_method,
                category=category,
                reference=reference,
                vendor_id=vendor_id,
                description=description,
                metadata_={
                    **({"attachments": attachments} if attachments else {}),
                    **({"financial_account_id": str(financial_account_id)} if financial_account_id else {}),
                } or None,
                created_by_account_id=created_by_account_id,
                transaction_date=transaction_date,
            )

    def record_vendor_payment(
        self,
        *,
        amount: Decimal,
        vendor_id: uuid.UUID,
        booking_id: uuid.UUID | None,
        cost_id: uuid.UUID | None,
        currency: str,
        payment_method: PaymentMethod,
        reference: str | None,
        description: str | None,
        recorded_by_account_id: uuid.UUID,
        transaction_date: datetime | None,
    ) -> FinancialTransaction:
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive.")
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            payable = self._system_account("2000", "Vendor Payable", "LIABILITY")
            source_code, source_name = {
                "RAZORPAY": ("1020", "Razorpay"),
                "BANK_TRANSFER": ("1010", "Bank"),
            }.get(payment_method.value, ("1000", "Cash"))
            source = self._system_account(source_code, source_name, "ASSET")
            transaction = self._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.VENDOR_PAYMENT,
                amount=amount,
                entries=[
                    {"account_id": payable.id, "debit": amount, "credit": Decimal("0"), "description": description},
                    {"account_id": source.id, "debit": Decimal("0"), "credit": amount, "description": description},
                ],
                vendor_id=vendor_id,
                booking_id=booking_id,
                currency=currency,
                payment_method=payment_method,
                reference=reference,
                description=description,
                created_by_account_id=recorded_by_account_id,
                transaction_date=transaction_date,
            )
            if cost_id is not None:
                cost = self.db.query(BookingCost).filter(BookingCost.id == cost_id).one_or_none()
                if cost is None:
                    raise HTTPException(status_code=404, detail="Booking cost not found.")
                if cost.vendor_id != vendor_id:
                    raise HTTPException(status_code=422, detail="Vendor payment does not match booking cost vendor.")
                new_paid = cost.paid_amount + amount
                if new_paid > cost.actual_amount:
                    raise HTTPException(status_code=422, detail="Vendor payment exceeds booking cost.")
                cost.paid_amount = new_paid
                cost.due_amount = max(Decimal("0"), cost.actual_amount - new_paid)
                cost.status = "PAID" if cost.due_amount == 0 else "PARTIALLY_PAID"
            self.db.add(AuditLog(
                account_id=recorded_by_account_id,
                action="VENDOR_PAYMENT_CREATED",
                entity_type="FinancialTransaction",
                entity_id=transaction.id,
                new_values={"amount": str(amount), "vendor_id": str(vendor_id), "booking_id": str(booking_id) if booking_id else None},
            ))
            return transaction

    def reverse_transaction(
        self,
        *,
        transaction_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> FinancialTransaction:
        transaction = self.db.query(FinancialTransaction).filter(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.status == FinancialTransactionStatus.POSTED,
        ).one_or_none()
        if transaction is None:
            raise HTTPException(status_code=404, detail="Posted financial transaction not found.")
        if not reason.strip():
            raise HTTPException(status_code=422, detail="A reversal reason is required.")
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            reversal = self._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.ADJUSTMENT,
                amount=transaction.amount,
                entries=[
                    {"account_id": entry.account_id, "debit": entry.credit, "credit": entry.debit, "description": reason}
                    for entry in transaction.entries
                ],
                customer_id=transaction.customer_id,
                vendor_id=transaction.vendor_id,
                booking_id=transaction.booking_id,
                quotation_id=transaction.quotation_id,
                enquiry_id=transaction.enquiry_id,
                currency=transaction.currency,
                payment_method=transaction.payment_method,
                reference=f"REVERSAL:{transaction.transaction_code}",
                external_reference=f"reversal:{transaction.id}",
                description=reason,
                created_by_account_id=actor_id,
            )
            transaction.status = FinancialTransactionStatus.REVERSED
            self.db.add(AuditLog(
                account_id=actor_id,
                action="FINANCIAL_TRANSACTION_REVERSED",
                entity_type="FinancialTransaction",
                entity_id=transaction.id,
                old_values={"status": FinancialTransactionStatus.POSTED.value},
                new_values={"status": FinancialTransactionStatus.REVERSED.value, "reversal_id": str(reversal.id), "reason": reason},
            ))
            return reversal
    def _create_transaction_in_current_transaction(
        self,
        *,
        transaction_type: FinancialTransactionType,
        amount: Decimal,
        entries: list[LedgerEntry],
        **attributes: object,
    ) -> FinancialTransaction:
        transaction = FinancialTransaction(
            transaction_code=f"FT-{uuid.uuid4().hex[:20].upper()}",
            transaction_type=transaction_type,
            status=FinancialTransactionStatus.POSTED,
            amount=amount,
            transaction_date=attributes.pop("transaction_date", None) or datetime.utcnow(),
            **attributes,
        )
        self.db.add(transaction)
        self.db.flush()
        self.db.add_all([
            FinancialTransactionEntry(transaction_id=transaction.id, **entry)
            for entry in entries
        ])
        self.db.flush()
        return transaction

    def create_customer_wallet(self, customer_id: uuid.UUID, customer_name: str) -> FinancialAccount:
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            existing = (
                self.db.query(FinancialAccount)
                .filter_by(owner_id=customer_id, account_type="LIABILITY", owner_type="CUSTOMER")
                .one_or_none()
            )
            if existing:
                return existing
            wallet = FinancialAccount(
                account_code=f"WALLET-{customer_id.hex[:12].upper()}",
                name=f"{customer_name} Wallet",
                account_type="LIABILITY",
                owner_type="CUSTOMER",
                owner_id=customer_id,
            )
            self.db.add(wallet)
            self.db.flush()
            return wallet
