import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor
from app.db.database import SessionLocal, get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.schemas.response import ActionResponse, SuccessResponse
from app.services.notification_service import NotificationService, actor_key, manager
from app.utils.security import decode_access_token

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=SuccessResponse[NotificationListResponse])
def list_notifications(limit: int = Query(default=50, ge=1, le=100), actor=Depends(get_current_actor), db: Session = Depends(get_db)):
    current, actor_type = actor
    items, unread = NotificationService(db).list_for_actor(actor_type, current.id, limit)
    return SuccessResponse(message="Notifications fetched successfully.", data=NotificationListResponse(items=items, unread_count=unread))


@router.patch("/{notification_id}/read", response_model=SuccessResponse[NotificationResponse])
def read_notification(notification_id: uuid.UUID, actor=Depends(get_current_actor), db: Session = Depends(get_db)):
    current, actor_type = actor
    item = NotificationService(db).mark_read(actor_type, current.id, notification_id)
    if not item:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return SuccessResponse(message="Notification marked as read.", data=item)


@router.post("/read-all", response_model=ActionResponse)
def read_all_notifications(actor=Depends(get_current_actor), db: Session = Depends(get_db)):
    current, actor_type = actor
    count = NotificationService(db).mark_all_read(actor_type, current.id)
    return ActionResponse(message=f"Marked {count} notifications as read.")


@router.websocket("/ws")
async def notifications_socket(websocket: WebSocket, token: str | None = Query(default=None)):
    access_token = token
    if not access_token:
        await websocket.close(code=1008, reason="Access token is required")
        return
    payload = decode_access_token(access_token)
    actor_type = payload.get("actor_type") if payload else None
    subject = payload.get("sub") if payload else None
    if actor_type not in {"CUSTOMER", "ADMIN", "STAFF"} or not subject:
        await websocket.close(code=1008, reason="Invalid access token")
        return
    try:
        actor_id = uuid.UUID(subject)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid actor")
        return

    db = SessionLocal()
    try:
        model = Customer if actor_type == "CUSTOMER" else User
        if not db.get(model, actor_id):
            await websocket.close(code=1008, reason="Actor not found")
            return
        key = actor_key(actor_type, actor_id)
        await manager.connect(key, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(key, websocket)
    finally:
        db.close()