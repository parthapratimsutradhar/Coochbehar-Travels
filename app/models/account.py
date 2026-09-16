from sqlalchemy import DateTime, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.enums import AccountRole
from app.models.base import ActiveEntity

class Account(ActiveEntity):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("email", "role", name="uq_accounts_email_role"),
        UniqueConstraint("mobile", "role", name="uq_accounts_mobile_role"),
    )

    account_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        index=True,
        nullable=True,
    )

    role: Mapped[AccountRole] = mapped_column(
        Enum(AccountRole, name="account_role"),
        nullable=False,
        index=True,
        default=AccountRole.CUSTOMER,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    profile_pic: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
# ── Relationships ───────────────────────────────────────────────────────    
    
    auth_sessions = relationship(
        "AuthSession",
        foreign_keys="AuthSession.account_id",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    customer_profile = relationship(
        "CustomerProfile",
        back_populates="account",
        uselist=False,
        cascade="all, delete-orphan",
    )

    enquiries = relationship(
        "Enquiry",
        back_populates="customer",
    )

    leads = relationship(
        "Lead",
        back_populates="customer",
    )

    lead_activities = relationship(
        "LeadActivity",
        back_populates="account",
    )

    quotations = relationship(
        "Quotation",
        foreign_keys="Quotation.customer_id",
        back_populates="customer",
    )

    bookings = relationship(
        "Booking",
        foreign_keys="Booking.customer_id",
        back_populates="customer",
    )

    notification_campaigns = relationship(
        "NotificationCampaign",
        foreign_keys="NotificationCampaign.recipient_id",
        back_populates="recipient",
        cascade="all, delete-orphan",
    )

    reviews = relationship(
        "Review",
        back_populates="customer",
    )

    tour_wishlists = relationship(
        "TourWishlist",
        back_populates="customer",
    )

    visitors = relationship(
        "Visitor",
        back_populates="customer",
    )

    referrals_made = relationship(
        "Referral",
        foreign_keys="Referral.referrer_customer_id",
        back_populates="referrer",
    )

    referral_received = relationship(
        "Referral",
        foreign_keys="Referral.referred_customer_id",
        back_populates="referred_customer",
    )

    updated_referral_config = relationship(
        "ReferralRewardConfig",
        foreign_keys="ReferralRewardConfig.updated_by_account_id",
        back_populates="updated_by",
    )

    approved_referral_rewards = relationship(
        "ReferralRewardHistory",
        foreign_keys="ReferralRewardHistory.approved_by_account_id",
        back_populates="approved_by",
    )

    documents_uploaded = relationship(
        "Document",
        foreign_keys="Document.uploaded_by_account_id",
        back_populates="uploaded_by_account",
    )

    documents_owned = relationship(
        "Document",
        foreign_keys="Document.customer_id",
        back_populates="customer",
    )

    documents_deleted = relationship(
        "Document",
        foreign_keys="Document.deleted_by_account_id",
        back_populates="deleted_by_account",
    )

    offer_usages = relationship(
        "TourOfferUsage",
        foreign_keys="TourOfferUsage.customer_id",
        back_populates="customer",
    )

    sales_bookings = relationship(
        "Booking",
        foreign_keys="Booking.sales_account_id",
        back_populates="sales_account",
    )

    created_bookings = relationship(
        "Booking",
        foreign_keys="Booking.created_by",
        back_populates="created_by_account",
    )