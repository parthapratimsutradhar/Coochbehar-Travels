import csv
import io
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, Response, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.enums import (
    FinancialTransactionStatus,
    FinancialTransactionType,
    PaymentMethod,
)
from app.models.account import Account
from app.models.financial_transaction import FinancialTransaction


class FinancialTransactionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def normalize_transaction_type(value: str | None) -> FinancialTransactionType:
        mapping = {
            "INCOME": FinancialTransactionType.BOOKING_PAYMENT,
            "EXPENSE": FinancialTransactionType.EXPENSE,
            "REFERRAL_INCOME": FinancialTransactionType.REFERRAL_REWARD,
            "REFERRAL": FinancialTransactionType.REFERRAL_REWARD,
            "BOOKING_PAYMENT": FinancialTransactionType.BOOKING_PAYMENT,
            "BOOKING_REFUND": FinancialTransactionType.BOOKING_REFUND,
            "WALLET_CREDIT": FinancialTransactionType.WALLET_CREDIT,
            "WALLET_DEBIT": FinancialTransactionType.WALLET_DEBIT,
            "VENDOR_PAYMENT": FinancialTransactionType.VENDOR_PAYMENT,
            "TRANSFER": FinancialTransactionType.TRANSFER,
            "ADJUSTMENT": FinancialTransactionType.ADJUSTMENT,
            "REFERRAL_REWARD": FinancialTransactionType.REFERRAL_REWARD,
        }
        normalized = (value or "EXPENSE").strip().upper()
        if normalized in mapping:
            return mapping[normalized]
        try:
            return FinancialTransactionType(normalized)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported transaction type: {value}",
            ) from exc

    @staticmethod
    def normalize_status(value: str | None) -> FinancialTransactionStatus:
        if value is None:
            return FinancialTransactionStatus.POSTED
        normalized = value.strip().upper()
        try:
            return FinancialTransactionStatus(normalized)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported transaction status: {value}",
            ) from exc

    @staticmethod
    def normalize_payment_method(value: str | None):
        if value is None:
            return None
        normalized = value.strip().upper()
        try:
            return PaymentMethod(normalized)
        except ValueError:
            return PaymentMethod.OTHER

    def create_transaction(self, payload: Any, actor: Account) -> FinancialTransaction:
        transaction_type = self.normalize_transaction_type(getattr(payload, "transaction_type", None))
        amount = Decimal(str(getattr(payload, "amount")))
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Amount must be greater than zero.")

        metadata = {
            "creditor": getattr(payload, "creditor", None),
            "debtor": getattr(payload, "debtor", None),
        }
        if getattr(payload, "vendor_id", None) is not None:
            metadata["vendor_id"] = str(payload.vendor_id)
        if getattr(payload, "booking_id", None) is not None:
            metadata["booking_id"] = str(payload.booking_id)
        if getattr(payload, "customer_id", None) is not None:
            metadata["customer_id"] = str(payload.customer_id)

        transaction = FinancialTransaction(
            transaction_code=f"FT-{uuid.uuid4().hex[:20].upper()}",
            transaction_type=transaction_type,
            amount=amount,
            currency=getattr(payload, "currency", "INR") or "INR",
            payment_method=self.normalize_payment_method(getattr(payload, "payment_method", None)),
            category=getattr(payload, "category", None),
            description=getattr(payload, "description", None),
            reference=getattr(payload, "reference", None),
            vendor_id=getattr(payload, "vendor_id", None),
            booking_id=getattr(payload, "booking_id", None),
            customer_id=getattr(payload, "customer_id", None),
            metadata_=metadata or None,
            transaction_date=getattr(payload, "transaction_date", None) or datetime.utcnow(),
            created_by_account_id=actor.id,
            status=self.normalize_status(getattr(payload, "status", None)),
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_transaction(self, transaction_id: uuid.UUID) -> FinancialTransaction:
        transaction = self.db.query(FinancialTransaction).filter(FinancialTransaction.id == transaction_id).one_or_none()
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial transaction not found.")
        return transaction

    def list_transactions(
        self,
        *,
        transaction_type: str | None = None,
        category: str | None = None,
        status: str | None = None,
        booking_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        query = self.db.query(FinancialTransaction)
        if transaction_type:
            query = query.filter(FinancialTransaction.transaction_type == self.normalize_transaction_type(transaction_type))
        if category:
            query = query.filter(FinancialTransaction.category.ilike(f"%{category}%"))
        if status:
            query = query.filter(FinancialTransaction.status == self.normalize_status(status))
        if booking_id:
            query = query.filter(FinancialTransaction.booking_id == booking_id)
        if customer_id:
            query = query.filter(FinancialTransaction.customer_id == customer_id)
        if vendor_id:
            query = query.filter(FinancialTransaction.vendor_id == vendor_id)
        if start_date:
            query = query.filter(FinancialTransaction.transaction_date >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(FinancialTransaction.transaction_date <= datetime.combine(end_date, datetime.max.time()))
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    FinancialTransaction.category.ilike(term),
                    FinancialTransaction.description.ilike(term),
                    FinancialTransaction.reference.ilike(term),
                    FinancialTransaction.transaction_code.ilike(term),
                )
            )
        query = query.order_by(FinancialTransaction.transaction_date.desc(), FinancialTransaction.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    def update_transaction(self, transaction_id: uuid.UUID, payload: Any, actor: Account) -> FinancialTransaction:
        transaction = self.get_transaction(transaction_id)
        if payload.amount is not None:
            amount = Decimal(str(payload.amount))
            if amount <= 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Amount must be greater than zero.")
            transaction.amount = amount
        if payload.transaction_type is not None:
            transaction.transaction_type = self.normalize_transaction_type(payload.transaction_type)
        if payload.category is not None:
            transaction.category = payload.category
        if payload.description is not None:
            transaction.description = payload.description
        if payload.transaction_date is not None:
            transaction.transaction_date = payload.transaction_date
        if payload.status is not None:
            transaction.status = self.normalize_status(payload.status)
        if payload.currency is not None:
            transaction.currency = payload.currency
        if payload.payment_method is not None:
            transaction.payment_method = self.normalize_payment_method(payload.payment_method)
        if payload.vendor_id is not None:
            transaction.vendor_id = payload.vendor_id
        if payload.booking_id is not None:
            transaction.booking_id = payload.booking_id
        if payload.customer_id is not None:
            transaction.customer_id = payload.customer_id
        if payload.reference is not None:
            transaction.reference = payload.reference

        metadata = dict(transaction.metadata_ or {})
        if payload.creditor is not None:
            metadata["creditor"] = payload.creditor
        if payload.debtor is not None:
            metadata["debtor"] = payload.debtor
        if payload.vendor_id is not None:
            metadata["vendor_id"] = str(payload.vendor_id)
        if payload.booking_id is not None:
            metadata["booking_id"] = str(payload.booking_id)
        if payload.customer_id is not None:
            metadata["customer_id"] = str(payload.customer_id)
        transaction.metadata_ = metadata or None
        transaction.created_by_account_id = transaction.created_by_account_id or actor.id
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def delete_transaction(self, transaction_id: uuid.UUID) -> None:
        transaction = self.get_transaction(transaction_id)
        transaction.status = FinancialTransactionStatus.CANCELLED
        self.db.commit()

    def get_summary(self, start_date: date | None = None, end_date: date | None = None) -> dict[str, Decimal | str | None]:
        query = self.db.query(FinancialTransaction).filter(FinancialTransaction.status == FinancialTransactionStatus.POSTED)
        if start_date:
            query = query.filter(FinancialTransaction.transaction_date >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(FinancialTransaction.transaction_date <= datetime.combine(end_date, datetime.max.time()))

        transactions = query.all()
        income = Decimal("0")
        expenses = Decimal("0")
        referral_income = Decimal("0")
        for transaction in transactions:
            if transaction.transaction_type in {FinancialTransactionType.BOOKING_PAYMENT, FinancialTransactionType.WALLET_CREDIT}:
                income += transaction.amount
            elif transaction.transaction_type == FinancialTransactionType.REFERRAL_REWARD:
                referral_income += transaction.amount
                income += transaction.amount
            elif transaction.transaction_type in {FinancialTransactionType.EXPENSE, FinancialTransactionType.VENDOR_PAYMENT}:
                expenses += transaction.amount
        net = income - expenses
        return {
            "total_income": income,
            "total_expenses": expenses,
            "referral_income": referral_income,
            "net_profit_loss": net,
        }

    def build_report(self, report_type: str, start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
        query = self.db.query(FinancialTransaction).filter(FinancialTransaction.status == FinancialTransactionStatus.POSTED)
        if start_date:
            query = query.filter(FinancialTransaction.transaction_date >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(FinancialTransaction.transaction_date <= datetime.combine(end_date, datetime.max.time()))

        normalized = (report_type or "income").strip().lower()
        if normalized == "income":
            query = query.filter(FinancialTransaction.transaction_type.in_([FinancialTransactionType.BOOKING_PAYMENT, FinancialTransactionType.REFERRAL_REWARD, FinancialTransactionType.WALLET_CREDIT]))
        elif normalized == "expenses":
            query = query.filter(FinancialTransaction.transaction_type.in_([FinancialTransactionType.EXPENSE, FinancialTransactionType.VENDOR_PAYMENT]))
        elif normalized == "referral_income":
            query = query.filter(FinancialTransaction.transaction_type == FinancialTransactionType.REFERRAL_REWARD)
        else:
            query = query.filter(FinancialTransaction.transaction_type.in_([FinancialTransactionType.BOOKING_PAYMENT, FinancialTransactionType.EXPENSE, FinancialTransactionType.REFERRAL_REWARD, FinancialTransactionType.VENDOR_PAYMENT]))

        rows = []
        for item in query.order_by(FinancialTransaction.transaction_date.desc()).all():
            meta = item.metadata_ or {}
            rows.append(
                {
                    "id": str(item.id),
                    "transaction_code": item.transaction_code,
                    "transaction_type": item.transaction_type.value,
                    "category": item.category,
                    "amount": str(item.amount),
                    "currency": item.currency,
                    "description": item.description,
                    "transaction_date": item.transaction_date.isoformat(),
                    "creditor": meta.get("creditor"),
                    "debtor": meta.get("debtor"),
                    "status": item.status.value,
                }
            )

        totals = {"amount": sum((Decimal(row["amount"]) for row in rows), Decimal("0"))}
        if normalized == "income":
            totals = {"income": sum((Decimal(row["amount"]) for row in rows), Decimal("0"))}
        elif normalized == "expenses":
            totals = {"expenses": sum((Decimal(row["amount"]) for row in rows), Decimal("0"))}
        elif normalized == "referral_income":
            totals = {"referral_income": sum((Decimal(row["amount"]) for row in rows), Decimal("0"))}

        return {"report_type": normalized, "rows": rows, "totals": totals}

    @staticmethod
    def export_csv(report_rows: list[dict], report_type: str) -> str:
        output = io.StringIO()
        fieldnames = ["transaction_code", "transaction_type", "category", "amount", "currency", "description", "transaction_date", "creditor", "debtor", "status"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in report_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
        return output.getvalue()

    @staticmethod
    def export_pdf(report_rows: list[dict], report_type: str) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements: list[Any] = [Paragraph(f"Finance report: {report_type.upper()}"), Spacer(1, 18)]
        data = [["Code", "Type", "Category", "Amount", "Date", "Status"]]
        for row in report_rows:
            data.append([
                row.get("transaction_code", ""),
                row.get("transaction_type", ""),
                row.get("category", ""),
                row.get("amount", "0"),
                row.get("transaction_date", ""),
                row.get("status", ""),
            ])
        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ]))
        elements.append(table)
        doc.build(elements)
        return buffer.getvalue()

    @staticmethod
    def export_excel(report_rows: list[dict], report_type: str) -> bytes:
        csv_blob = FinancialTransactionService.export_csv(report_rows, report_type)
        return csv_blob.encode("utf-8")
