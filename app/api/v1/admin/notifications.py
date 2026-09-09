from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.models.account import Account
from app.schemas.notification import AdminNotificationCreate, NotificationCreate, NotificationResponse
from app.schemas.response import SuccessResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/notifications", tags=["Admin - Notifications"])


@router.post("", response_model=SuccessResponse[list[NotificationResponse]], status_code=status.HTTP_201_CREATED)
async def create_notifications(
    payload: AdminNotificationCreate,
    _: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    customer_ids = service.customer_ids(payload.customer_ids, payload.broadcast_customers)
    user_ids = service.user_ids(payload.user_ids, payload.broadcast_staff)
    all_recipients = list(dict.fromkeys(customer_ids + user_ids))
    if not all_recipients:
        raise HTTPException(status_code=422, detail="Provide recipient IDs or enable a broadcast target")

    notification_payload = payload.model_dump(
        exclude={"customer_ids", "user_ids", "broadcast_customers", "broadcast_staff"}
    )
    item = service.create(NotificationCreate(**notification_payload), recipient_ids=all_recipients)
    await service.publish(item)

    response_item = NotificationResponse(
        id=item.id,
        notification_type=item.notification_type,
        title=item.title,
        message=item.message,
        image_url=item.image_url,
        action_url=item.action_url,
        data=item.data,
        expires_at=item.expires_at,
        created_at=item.created_at,
        recipient_ids=item.recipient_ids,
    )
    return SuccessResponse(message=f"Created notification for {len(all_recipients)} recipient(s).", data=[response_item])