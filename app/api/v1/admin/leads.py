import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.messages.success import LeadSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.lead import (
	AdminLeadActivityCreate,
	LeadActivityResponse,
	LeadActivityUpdate,
	LeadAssignmentUpdate,
	LeadManageUpdate,
	LeadStatusUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse
from app.services.lead_service import LeadService

router = APIRouter(
	prefix="/admin/leads",
	tags=["Admin - Leads"],
)


@router.put(
	"/{lead_id}/assignment",
	response_model=ActionResponse,
	summary="Assign or unassign a lead (Admin)",
)
def update_lead_assignment(
	lead_id: uuid.UUID,
	payload: LeadAssignmentUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	LeadService(db).manage_lead(
		lead_id,
		LeadManageUpdate(assigned_account_id=payload.assigned_account_id),
		current_user.id,
	)
	return ActionResponse(message=LeadSuccess.UPDATED)


@router.patch(
	"/{lead_id}/status",
	response_model=ActionResponse,
	summary="Update a lead status (Admin)",
)
def update_lead_status(
	lead_id: uuid.UUID,
	payload: LeadStatusUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	LeadService(db).manage_lead(
		lead_id,
		LeadManageUpdate(
			status=payload.status,
			lost_reason=payload.lost_reason,
			lost_reason_notes=payload.lost_reason_notes,
		),
		current_user.id,
	)
	return ActionResponse(message=LeadSuccess.UPDATED)


@router.post(
	"/{lead_id}/activities",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Add a lead activity (Admin)",
)
def create_lead_activity(
	lead_id: uuid.UUID,
	payload: AdminLeadActivityCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	LeadService(db).create_activity(lead_id, payload, current_user.id)
	return ActionResponse(message=LeadSuccess.ACTIVITY_CREATED)


@router.patch(
	"/{lead_id}/activities/{activity_id}",
	response_model=ActionResponse,
	summary="Update a lead activity (Admin)",
)
def update_lead_activity(
	lead_id: uuid.UUID,
	activity_id: uuid.UUID,
	payload: LeadActivityUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	del current_user
	LeadService(db).update_activity(lead_id, activity_id, payload)
	return ActionResponse(message=LeadSuccess.UPDATED)


@router.delete(
	"/{lead_id}/activities/{activity_id}",
	response_model=ActionResponse,
	summary="Delete a lead activity (Admin)",
)
def delete_lead_activity(
	lead_id: uuid.UUID,
	activity_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	del current_user
	LeadService(db).delete_activity(lead_id, activity_id)
	return ActionResponse(message=LeadSuccess.DELETED)


@router.get(
	"/{lead_id}/activities",
	response_model=PaginatedResponse[LeadActivityResponse],
	summary="List lead activities (Admin)",
)
def list_lead_activities(
	lead_id: uuid.UUID,
	view: str = Query("all", pattern="^(all|upcoming|today|overdue)$"),
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	del current_user
	service = LeadService(db)
	activities = service.list_activities(
		lead_id,
		skip=(page - 1) * page_size,
		limit=page_size,
		view=view,
	)
	total_items = service.count_activities(lead_id, view=view)
	total_pages = (total_items + page_size - 1) // page_size
	return PaginatedResponse(
		message=LeadSuccess.ACTIVITIES_RETRIEVED,
		data=[LeadActivityResponse.model_validate(activity) for activity in activities],
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=total_items,
			total_pages=total_pages,
			has_next=page < total_pages,
			has_previous=page > 1,
		),
	)
