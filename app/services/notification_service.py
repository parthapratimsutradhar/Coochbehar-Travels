import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationResponse


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
        payload = {"event": "notification.created", "data": NotificationResponse.model_validate(notification).model_dump(mode="json")}
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

    def list_for_actor(self, actor_type: str, actor_id: uuid.UUID, limit: int = 50) -> tuple[list[Notification], int]:
        owner = Notification.customer_id if actor_type == "CUSTOMER" else Notification.user_id
        filters = [owner == actor_id, or_(Notification.expires_at.is_(None), Notification.expires_at > datetime.now(timezone.utc))]
        items = list(self.db.scalars(select(Notification).where(*filters).order_by(Notification.created_at.desc()).limit(limit)))
        unread = self.db.scalar(select(func.count()).select_from(Notification).where(*filters, Notification.is_read.is_(False))) or 0
        return items, unread

    def mark_read(self, actor_type: str, actor_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
        owner = Notification.customer_id if actor_type == "CUSTOMER" else Notification.user_id
        item = self.db.scalar(select(Notification).where(Notification.id == notification_id, owner == actor_id))
        if not item:
            return None
        if not item.is_read:
            item.is_read = True
            item.read_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(item)
        return item

    def mark_all_read(self, actor_type: str, actor_id: uuid.UUID) -> int:
        owner = Notification.customer_id if actor_type == "CUSTOMER" else Notification.user_id
        result = self.db.execute(update(Notification).where(owner == actor_id, Notification.is_read.is_(False)).values(is_read=True, read_at=datetime.now(timezone.utc)))
        self.db.commit()
        return result.rowcount

    def create(self, payload: NotificationCreate, *, customer_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None) -> Notification:
        if (customer_id is None) == (user_id is None):
            raise ValueError("Exactly one notification recipient is required")
        item = Notification(**payload.model_dump(), customer_id=customer_id, user_id=user_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def customer_ids(self, ids: list[uuid.UUID] | None, broadcast: bool) -> list[uuid.UUID]:
        if ids:
            return ids
        if broadcast:
            return list(self.db.scalars(select(Customer.id)))
        return []

    def user_ids(self, ids: list[uuid.UUID] | None, broadcast: bool) -> list[uuid.UUID]:
        if ids:
            return ids
        if broadcast:
            return list(self.db.scalars(select(User.id).where(User.is_active.is_(True))))
        return []

    async def publish(self, item: Notification) -> None:
        if item.customer_id:
            recipient_type = "CUSTOMER"
            recipient_id = item.customer_id
        else:
            recipient_type = self.db.scalar(select(User.role).where(User.id == item.user_id))
            recipient_type = getattr(recipient_type, "value", str(recipient_type))
            recipient_id = item.user_id
        await manager.publish(actor_key(recipient_type, recipient_id), item)