from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.models.user import User
from app.schemas.notification import AdminNotificationCreate, NotificationCreate, NotificationResponse
from app.schemas.response import SuccessResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/notifications", tags=["Admin - Notifications"])


@router.post("", response_model=SuccessResponse[list[NotificationResponse]], status_code=status.HTTP_201_CREATED)
async def create_notifications(payload: AdminNotificationCreate, _: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    service = NotificationService(db)
    customer_ids = service.customer_ids(payload.customer_ids, payload.broadcast_customers)
    user_ids = service.user_ids(payload.user_ids, payload.broadcast_staff)
    if not customer_ids and not user_ids:
        raise HTTPException(status_code=422, detail="Provide recipient IDs or enable a broadcast target")
    created = []
    notification_payload = payload.model_dump(exclude={"customer_ids", "user_ids", "broadcast_customers", "broadcast_staff"})
    for customer_id in customer_ids:
        item = service.create(NotificationCreate(**notification_payload), customer_id=customer_id)
        created.append(item)
        await service.publish(item)
    for user_id in user_ids:
        item = service.create(NotificationCreate(**notification_payload), user_id=user_id)
        created.append(item)
        await service.publish(item)
    return SuccessResponse(message=f"Created {len(created)} notifications.", data=created)