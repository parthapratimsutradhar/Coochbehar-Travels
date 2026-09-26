import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import (
    AccountRole,
    FinancialAccountOwnerType,
    FinancialAccountType,
    FinancialTransactionStatus,
    FinancialTransactionType,
    PaymentMethod,
    PaymentStatus,
)
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.booking import Booking
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry
from app.services.financial_service import FinancialService


class WalletService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.financial = FinancialService(db)

    def get_wallet_account(self, customer_id: uuid.UUID) -> FinancialAccount:
        wallet = (
            self.db.query(FinancialAccount)
            .filter(
                FinancialAccount.owner_id == customer_id,
                FinancialAccount.owner_type == FinancialAccountOwnerType.CUSTOMER,
                FinancialAccount.account_type == FinancialAccountType.LIABILITY,
            )
            .one_or_none()
        )
        if wallet is None:
            customer = self.db.query(Account).filter(
                Account.id == customer_id,
                Account.role == AccountRole.CUSTOMER,
            ).one_or_none()
            if customer is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
            wallet = self.financial.create_customer_wallet(customer.id, customer.name)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet is inactive.")
        return wallet

    def balance(self, wallet: FinancialAccount) -> Decimal:
        credits = self.db.query(func.coalesce(func.sum(FinancialTransactionEntry.credit), 0)).join(
            FinancialTransaction,
            FinancialTransaction.id == FinancialTransactionEntry.transaction_id,
        ).filter(
            FinancialTransactionEntry.account_id == wallet.id,
            FinancialTransaction.status == FinancialTransactionStatus.POSTED,
        ).scalar() or Decimal("0")
        debits = self.db.query(func.coalesce(func.sum(FinancialTransactionEntry.debit), 0)).join(
            FinancialTransaction,
            FinancialTransaction.id == FinancialTransactionEntry.transaction_id,
        ).filter(
            FinancialTransactionEntry.account_id == wallet.id,
            FinancialTransaction.status == FinancialTransactionStatus.POSTED,
        ).scalar() or Decimal("0")
        return Decimal(credits) - Decimal(debits)

    def history(self, customer_id: uuid.UUID, limit: int = 100) -> list[FinancialTransaction]:
        wallet = self.get_wallet_account(customer_id)
        return list(
            self.db.query(FinancialTransaction)
            .join(FinancialTransactionEntry, FinancialTransactionEntry.transaction_id == FinancialTransaction.id)
            .filter(FinancialTransactionEntry.account_id == wallet.id)
            .order_by(FinancialTransaction.transaction_date.desc())
            .limit(limit)
            .all()
        )

    def record_top_up(
        self,
        *,
        customer_id: uuid.UUID,
        amount: Decimal,
        payment_method: PaymentMethod,
        payment_status: PaymentStatus,
        gateway: str | None,
        gateway_transaction_id: str | None,
        external_reference: str,
        description: str | None,
    ) -> FinancialTransaction:
        existing = self.db.query(FinancialTransaction).filter(
            FinancialTransaction.external_reference == external_reference
        ).one_or_none()
        if existing is not None:
            return existing
        wallet = self.get_wallet_account(customer_id)
        if payment_status != PaymentStatus.SUCCESS:
            if self.db.in_transaction():
                self.db.commit()
            with self.db.begin():
                transaction = FinancialTransaction(
                    transaction_code=f"FT-{uuid.uuid4().hex[:20].upper()}",
                    transaction_type=FinancialTransactionType.INCOME,
                    status={
                        PaymentStatus.PENDING: FinancialTransactionStatus.PENDING,
                        PaymentStatus.CANCELLED: FinancialTransactionStatus.CANCELLED,
                        PaymentStatus.FAILED: FinancialTransactionStatus.FAILED,
                        PaymentStatus.REFUNDED: FinancialTransactionStatus.REVERSED,
                    }[payment_status],
                    amount=amount,
                    currency=wallet.currency,
                    payment_method=payment_method,
                    external_reference=external_reference,
                    gateway=gateway,
                    gateway_transaction_id=gateway_transaction_id,
                    customer_id=customer_id,
                    description=description,
                )
                self.db.add(transaction)
                self.db.flush()
                return transaction
        if not gateway_transaction_id and payment_method not in {PaymentMethod.CASH, PaymentMethod.OFFLINE}:
            raise HTTPException(status_code=422, detail="A verified gateway transaction reference is required.")
        source_code = "1000" if payment_method in {PaymentMethod.CASH, PaymentMethod.OFFLINE} else "1020"
        source_name = "Cash" if source_code == "1000" else "Payment Gateway"
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            source = self.financial._system_account(source_code, source_name, "ASSET")
            return self.financial._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.INCOME,
                amount=amount,
                entries=[
                    {"account_id": source.id, "debit": amount, "credit": Decimal("0"), "description": description},
                    {"account_id": wallet.id, "debit": Decimal("0"), "credit": amount, "description": description},
                ],
                currency=wallet.currency,
                payment_method=payment_method,
                external_reference=external_reference,
                gateway=gateway,
                gateway_transaction_id=gateway_transaction_id,
                customer_id=customer_id,
                description=description,
            )

    def pay_booking(self, *, customer: Account, booking: Booking, amount: Decimal, description: str | None) -> FinancialTransaction:
        if booking.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="Booking does not belong to this customer.")
        if amount > booking.due_amount:
            raise HTTPException(status_code=422, detail="Payment exceeds the booking outstanding amount.")
        wallet = self.get_wallet_account(customer.id)
        if amount > self.balance(wallet):
            raise HTTPException(status_code=422, detail="Insufficient wallet balance.")
        receivable = self.financial._system_account("1100", "Customer Receivable", "ASSET")
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            transaction = self.financial._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.INCOME,
                amount=amount,
                entries=[
                    {"account_id": wallet.id, "debit": amount, "credit": Decimal("0"), "description": description},
                    {"account_id": receivable.id, "debit": Decimal("0"), "credit": amount, "description": description},
                ],
                booking_id=booking.id,
                customer_id=customer.id,
                currency=wallet.currency,
                payment_method=PaymentMethod.WALLET,
                description=description,
                created_by_account_id=customer.id,
            )
        booking.paid_amount += amount
        booking.due_amount = max(Decimal("0"), booking.total_amount - booking.paid_amount)
        self.db.commit()
        return transaction

    def adjust(self, *, customer_id: uuid.UUID, amount: Decimal, direction: str, reason: str, actor: Account, reference: str | None) -> FinancialTransaction:
        wallet = self.get_wallet_account(customer_id)
        if direction == "DEBIT" and amount > self.balance(wallet):
            raise HTTPException(status_code=422, detail="Insufficient wallet balance.")
        old_balance = self.balance(wallet)
        source = self.financial._system_account("6000", "Wallet Adjustments", "EXPENSE")
        debit_wallet = direction == "DEBIT"
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            transaction = self.financial._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.EXPENSE,
                amount=amount,
                entries=[
                    {"account_id": wallet.id, "debit": amount if debit_wallet else Decimal("0"), "credit": Decimal("0") if debit_wallet else amount, "description": reason},
                    {"account_id": source.id, "debit": Decimal("0") if debit_wallet else amount, "credit": amount if debit_wallet else Decimal("0"), "description": reason},
                ],
                customer_id=customer_id,
                currency=wallet.currency,
                payment_method=PaymentMethod.OFFLINE,
                reference=reference,
                description=reason,
                created_by_account_id=actor.id,
            )
            self.db.add(AuditLog(
                account_id=actor.id,
                action="WALLET_ADJUSTMENT",
                entity_type="FinancialAccount",
                entity_id=wallet.id,
                old_values={"balance": str(old_balance)},
                new_values={"amount": str(amount), "direction": direction, "reason": reason, "transaction_id": str(transaction.id)},
            ))
            self.db.flush()
            return transaction

    def refund_to_wallet(
        self,
        *,
        customer_id: uuid.UUID,
        amount: Decimal,
        booking_id: uuid.UUID | None,
        reason: str,
        reference: str,
        actor: Account,
    ) -> FinancialTransaction:
        external_reference = f"wallet-refund:{reference}"
        existing = self.db.query(FinancialTransaction).filter(
            FinancialTransaction.external_reference == external_reference,
        ).one_or_none()
        if existing is not None:
            return existing
        wallet = self.get_wallet_account(customer_id)
        receivable = self.financial._system_account("1100", "Customer Receivable", "ASSET")
        if self.db.in_transaction():
            self.db.commit()
        with self.db.begin():
            transaction = self.financial._create_transaction_in_current_transaction(
                transaction_type=FinancialTransactionType.EXPENSE,
                amount=amount,
                entries=[
                    {"account_id": receivable.id, "debit": amount, "credit": Decimal("0"), "description": reason},
                    {"account_id": wallet.id, "debit": Decimal("0"), "credit": amount, "description": reason},
                ],
                customer_id=customer_id,
                booking_id=booking_id,
                currency=wallet.currency,
                payment_method=PaymentMethod.OFFLINE,
                external_reference=external_reference,
                reference=reference,
                description=reason,
                created_by_account_id=actor.id,
            )
            self.db.add(AuditLog(
                account_id=actor.id,
                action="WALLET_REFUND_CREATED",
                entity_type="FinancialTransaction",
                entity_id=transaction.id,
                new_values={"customer_id": str(customer_id), "amount": str(amount), "reason": reason},
            ))
            return transaction
