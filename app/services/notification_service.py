import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.enums import AccountRole
from app.models.account import Account
from app.models.notification import Notification
from app.models.notification_campaign import NotificationCampaign
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.services.socket_service import publish_notification


class NotificationConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, key: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(key, set()).add(websocket)

    def disconnect(self, key: str, websocket: WebSocket) -> None:
        sockets = self.connections.get(key)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self.connections.pop(key, None)

    async def publish(self, key: str, notification: Notification) -> None:
        response_data = NotificationResponse(
            id=notification.id,
            notification_type=notification.notification_type,
            title=notification.title,
            message=notification.message,
            image_url=notification.image_url,
            action_url=notification.action_url,
            data=notification.data,
            expires_at=notification.expires_at,
            created_at=notification.created_at,
            recipient_ids=notification.recipient_ids,
        )
        payload = {
            "event": "notification.created",
            "data": response_data.model_dump(mode="json"),
        }
        sockets = list(self.connections.get(key, set()))
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(key, websocket)


manager = NotificationConnectionManager()


def actor_key(actor_type: str, actor_id: uuid.UUID) -> str:
    return f"{actor_type}:{actor_id}"


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def to_response(campaign: NotificationCampaign) -> NotificationResponse:
        notif = campaign.notification
        return NotificationResponse(
            id=campaign.id,
            notification_type=notif.notification_type if notif else "GENERAL",
            title=notif.title if notif else "",
            message=notif.message if notif else "",
            image_url=notif.image_url if notif else None,
            action_url=notif.action_url if notif else None,
            data=notif.data if notif else None,
            is_delivered=campaign.is_delivered,
            delivered_at=campaign.delivered_at,
            is_read=campaign.is_read,
            read_at=campaign.read_at,
            expires_at=notif.expires_at if notif else None,
            created_at=campaign.created_at,
            recipient_id=campaign.recipient_id,
            recipient_ids=notif.recipient_ids if notif else None,
        )

    def list_for_actor(
        self,
        actor_type: str,
        actor_id: uuid.UUID,
        limit: int = 50,
    ) -> tuple[list[NotificationResponse], int]:
        filters = [
            NotificationCampaign.recipient_id == actor_id,
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.now(timezone.utc),
            ),
        ]
        stmt = (
            select(NotificationCampaign)
            .join(NotificationCampaign.notification)
            .where(*filters)
            .order_by(NotificationCampaign.created_at.desc())
            .limit(limit)
        )
        items = list(self.db.scalars(stmt))
        unread = self.db.scalar(
            select(func.count())
            .select_from(NotificationCampaign)
            .join(NotificationCampaign.notification)
            .where(*filters, NotificationCampaign.is_read.is_(False))
        ) or 0
        return [self.to_response(item) for item in items], unread

    def mark_read(
        self,
        actor_type: str,
        actor_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> NotificationResponse | None:
        item = self.db.scalar(
            select(NotificationCampaign).where(
                or_(
                    NotificationCampaign.id == notification_id,
                    NotificationCampaign.notification_id == notification_id,
                ),
                NotificationCampaign.recipient_id == actor_id,
            )
        )
        if not item:
            return None
        if not item.is_read:
            item.is_read = True
            item.read_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(item)
        return self.to_response(item)

    def mark_all_read(self, actor_type: str, actor_id: uuid.UUID) -> int:
        result = self.db.execute(
            update(NotificationCampaign)
            .where(
                NotificationCampaign.recipient_id == actor_id,
                NotificationCampaign.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()
        return result.rowcount

    def create(
        self,
        payload: NotificationCreate,
        *,
        recipient_ids: list[uuid.UUID] | None = None,
        customer_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Notification:
        recipients: list[uuid.UUID] = list(recipient_ids or [])
        if customer_id and customer_id not in recipients:
            recipients.append(customer_id)
        if user_id and user_id not in recipients:
            recipients.append(user_id)

        if not recipients:
            raise ValueError("At least one notification recipient is required")

        item = Notification(
            notification_type=payload.notification_type,
            title=payload.title,
            message=payload.message,
            image_url=payload.image_url,
            action_url=payload.action_url,
            data=payload.data,
            expires_at=payload.expires_at,
            recipient_ids=recipients,
        )
        self.db.add(item)
        self.db.flush()

        for rec_id in recipients:
            campaign = NotificationCampaign(
                notification_id=item.id,
                recipient_id=rec_id,
                is_delivered=True,
                delivered_at=datetime.now(timezone.utc),
                is_read=False,
            )
            self.db.add(campaign)

        self.db.commit()
        self.db.refresh(item)
        return item

    def customer_ids(self, ids: list[uuid.UUID] | None, broadcast: bool) -> list[uuid.UUID]:
        if ids:
            return ids
        if broadcast:
            return list(self.db.scalars(select(Account.id).where(Account.role == AccountRole.CUSTOMER)))
        return []

    def user_ids(self, ids: list[uuid.UUID] | None, broadcast: bool) -> list[uuid.UUID]:
        if ids:
            return ids
        if broadcast:
            return list(self.db.scalars(select(Account.id).where(Account.is_active.is_(True))))
        return []

    async def publish(self, item: Notification) -> None:
        recipients = item.recipient_ids or []
        for rec_id in recipients:
            role = self.db.scalar(select(Account.role).where(Account.id == rec_id))
            role_val = getattr(role, "value", str(role)).upper() if role else "CUSTOMER"
            actor_type = "CUSTOMER" if role_val == "CUSTOMER" else "ADMIN"
            await manager.publish(actor_key(actor_type, rec_id), item)
        await publish_notification(item, db=self.db)

    async def notify_admins(
        self,
        *,
        notification_type: str,
        title: str,
        message: str,
        data: dict | None = None,
        action_url: str | None = None,
    ) -> Notification | None:
        """Persist and broadcast an event to every active admin/staff member."""
        admin_ids = list(
            self.db.scalars(
                select(Account.id).where(
                    Account.is_active.is_(True),
                    Account.role.in_((AccountRole.ADMIN, AccountRole.STAFF)),
                )
            )
        )
        if not admin_ids:
            return None
        payload = NotificationCreate(
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            action_url=action_url,
        )
        item = self.create(payload, recipient_ids=admin_ids)
        await self.publish(item)
        return item

    async def notify_customer(
        self,
        customer_id: uuid.UUID,
        *,
        notification_type: str,
        title: str,
        message: str,
        data: dict | None = None,
        action_url: str | None = None,
    ) -> Notification:
        payload = NotificationCreate(
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            action_url=action_url,
        )
        item = self.create(payload, recipient_ids=[customer_id])
        await self.publish(item)
        return item