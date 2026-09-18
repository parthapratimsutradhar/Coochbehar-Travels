import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import AccountRole, LeadChannel, LeadStatus
from app.core.messages.error import LeadError
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.repository.audit_repo import AuditRepository
from app.repository.account_repo import AccountRepository
from app.repository.lead_repo import LeadRepository
from app.schemas.lead import LeadActivityCreate, LeadActivityUpdate, LeadManageUpdate
from app.services.lead_scoring_service import LeadScoringService
from app.services.socket_service import emit_lead_activity_created, emit_lead_score_updated


class LeadService:
    def __init__(self, db: Session) -> None:
        self.lead_repo = LeadRepository(db)
        self.account_repo = AccountRepository(db)
        self.audit_repo = AuditRepository(db)
        self.scoring_service = LeadScoringService(db)

    def get_lead_for_enquiry(self, enquiry_id: uuid.UUID) -> Lead:
        lead = self.lead_repo.get_by_enquiry_id_with_activities(enquiry_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=LeadError.LEAD_NOT_FOUND)
        return lead

    def list_activities(
        self,
        lead_id: uuid.UUID,
        *,
        skip: int,
        limit: int,
        view: str,
    ) -> list[LeadActivity]:
        self._get_lead(lead_id)
        return self.lead_repo.list_activities(
            lead_id,
            skip=skip,
            limit=limit,
            view=view,
            now=datetime.now(timezone.utc),
        )

    def count_activities(self, lead_id: uuid.UUID, *, view: str) -> int:
        self._get_lead(lead_id)
        return self.lead_repo.count_activities(
            lead_id,
            view=view,
            now=datetime.now(timezone.utc),
        )

    def manage_lead(
        self,
        lead_id: uuid.UUID,
        payload: LeadManageUpdate,
        account_id: uuid.UUID,
    ) -> None:
        lead = self._get_lead(lead_id)
        now = datetime.now(timezone.utc)
        old_values = self._state(lead)
        effective_status = payload.status or lead.status

        if effective_status != LeadStatus.LOST and (
            payload.lost_reason is not None or payload.lost_reason_notes is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=LeadError.LOST_REASON_ONLY_FOR_LOST,
            )
        if effective_status == LeadStatus.LOST and not payload.lost_reason and lead.lost_reason is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=LeadError.LOST_REASON_REQUIRED,
            )

        if "assigned_account_id" in payload.model_fields_set:
            if payload.assigned_account_id is not None:
                assignee = self.account_repo.get_admin_staff_by_id(payload.assigned_account_id)
                if not assignee or not assignee.is_active or assignee.role not in (AccountRole.ADMIN, AccountRole.STAFF):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=LeadError.ASSIGNEE_NOT_FOUND,
                    )
            lead.assigned_account_id = payload.assigned_account_id
        if payload.qualification_notes is not None:
            lead.qualification_notes = payload.qualification_notes
        if payload.lost_reason is not None:
            lead.lost_reason = payload.lost_reason
        if payload.lost_reason_notes is not None:
            lead.lost_reason_notes = payload.lost_reason_notes
        if payload.status is not None:
            lead.status = payload.status
            if payload.status != LeadStatus.LOST:
                lead.lost_reason = None
                lead.lost_reason_notes = None
            if payload.status == LeadStatus.QUALIFIED and lead.qualified_at is None:
                lead.qualified_at = now
            elif payload.status == LeadStatus.CONVERTED:
                lead.converted_at = now
            elif payload.status == LeadStatus.LOST:
                lead.lost_at = now

        new_values = self._state(lead)
        if old_values != new_values:
            self.lead_repo.add_activity(
                LeadActivity(
                    lead_id=lead.id,
                    account_id=account_id,
                    channel=LeadChannel.OFFLINE,
                    activity_type="STATUS_CHANGED",
                    notes=f"Lead updated: {new_values}",
                )
            )
        self.audit_repo.add_change(
            account_id=account_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_UPDATED",
            old_values=old_values,
            new_values=new_values,
        )
        self.lead_repo.save()

    def create_activity(
        self,
        lead_id: uuid.UUID,
        payload: LeadActivityCreate,
        account_id: uuid.UUID,
    ) -> LeadActivity:
        lead = self._get_lead(lead_id)
        activity = LeadActivity(
            lead_id=lead_id,
            account_id=payload.account_id or payload.user_id or account_id,
            channel=payload.channel,
            activity_type=payload.activity_type,
            notes=payload.notes,
            next_follow_up_at=payload.next_follow_up_at,
        )
        self.lead_repo.add_activity(activity)
        lead.last_contacted_at = datetime.now(timezone.utc)
        delta = self.scoring_service.calculate_activity_score(activity)
        previous_score, new_score, actual_delta = self.scoring_service.apply_score_change(lead, delta)
        self.lead_repo.save()
        emit_lead_activity_created(lead, activity)
        if actual_delta > 0:
            emit_lead_score_updated(
                lead,
                previous_score=previous_score,
                new_score=new_score,
                delta=actual_delta,
                reason=f"ACTIVITY_{activity.activity_type.upper()}",
            )
        return activity

    def update_activity(
        self,
        lead_id: uuid.UUID,
        activity_id: uuid.UUID,
        payload: LeadActivityUpdate,
    ) -> None:
        lead = self._get_lead(lead_id)
        activity = self.lead_repo.get_activity(activity_id, lead_id)
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=LeadError.ACTIVITY_NOT_FOUND,
            )

        previous_delta = self.scoring_service.calculate_activity_score(activity)
        for field in ("channel", "activity_type", "notes", "next_follow_up_at"):
            if field in payload.model_fields_set:
                setattr(activity, field, getattr(payload, field))
        new_delta = self.scoring_service.calculate_activity_score(activity)
        score_delta = new_delta - previous_delta
        if score_delta:
            previous_score, new_score, actual_delta = self.scoring_service.apply_score_change(lead, score_delta)
        else:
            previous_score = new_score = lead.lead_score
            actual_delta = 0
        self.lead_repo.save()
        if actual_delta:
            emit_lead_score_updated(
                lead,
                previous_score=previous_score,
                new_score=new_score,
                delta=actual_delta,
                reason=f"ACTIVITY_UPDATED_{activity.activity_type.upper()}",
            )

    def delete_activity(self, lead_id: uuid.UUID, activity_id: uuid.UUID) -> None:
        lead = self._get_lead(lead_id)
        activity = self.lead_repo.get_activity(activity_id, lead_id)
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=LeadError.ACTIVITY_NOT_FOUND,
            )

        delta = self.scoring_service.calculate_activity_score(activity)
        previous_score, new_score, actual_delta = self.scoring_service.apply_score_change(lead, -delta)
        self.lead_repo.delete_activity(activity)
        self.lead_repo.save()
        if actual_delta:
            emit_lead_score_updated(
                lead,
                previous_score=previous_score,
                new_score=new_score,
                delta=actual_delta,
                reason=f"ACTIVITY_DELETED_{activity.activity_type.upper()}",
            )

    def _get_lead(self, lead_id: uuid.UUID) -> Lead:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=LeadError.LEAD_NOT_FOUND)
        return lead

    @staticmethod
    def _state(lead: Lead) -> dict:
        return {
            "assigned_account_id": str(lead.assigned_account_id) if lead.assigned_account_id else None,
            "status": lead.status.value,
            "qualification_notes": lead.qualification_notes,
            "lost_reason": lead.lost_reason,
        }
