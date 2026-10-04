import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import BackupGroup
from app.core.messages.error import BackupError
from app.core.messages.success import BackupSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.response import ActionResponse, ErrorResponse
from app.services.backup_service import BackupService, MAX_BACKUP_SIZE


router = APIRouter(prefix="/admin/backups", tags=["Admin - Backups"])


def _database_conflict_details(exc: SQLAlchemyError) -> dict[str, str]:
	original = getattr(exc, "orig", exc)
	diag = getattr(original, "diag", None)
	if diag is not None:
		sqlstate = getattr(diag, "sqlstate", None)
		reasons = {
			"23502": "not_null_violation",
			"23505": "unique_constraint_violation",
			"23503": "foreign_key_violation",
			"23514": "check_constraint_violation",
		}
		details = {
			key: value
			for key, value in (
				("reason", reasons.get(sqlstate, "database_constraint_violation")),
				("sqlstate", sqlstate),
				("table", getattr(diag, "table_name", None)),
				("column", getattr(diag, "column_name", None)),
				("constraint", getattr(diag, "constraint_name", None)),
			)
			if value
		}
		if details:
			return details

	message = str(original)
	not_null_match = re.search(
		r"NOT NULL constraint failed: ([\w]+)\.([\w]+)", message, re.IGNORECASE
	)
	if not_null_match:
		return {
			"reason": "not_null_violation",
			"table": not_null_match.group(1),
			"column": not_null_match.group(2),
		}
	unique_match = re.search(r"UNIQUE constraint failed: (.+)", message, re.IGNORECASE)
	if unique_match:
		return {
			"reason": "unique_constraint_violation",
			"columns": unique_match.group(1),
		}
	check_match = re.search(r"CHECK constraint failed: (.+)", message, re.IGNORECASE)
	if check_match:
		return {
			"reason": "check_constraint_violation",
			"constraint": check_match.group(1),
		}
	if "FOREIGN KEY constraint failed" in message:
		return {"reason": "foreign_key_violation"}
	return {"reason": "database_constraint_violation"}


@router.get(
	"/export",
	summary="Export selected admin data",
	responses={
		200: {
			"content": {
				"application/json": {},
				"application/zip": {},
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
			},
		},
		401: {"model": ErrorResponse},
		403: {"model": ErrorResponse},
		422: {"model": ErrorResponse},
	},
)
def export_admin_backup(
	groups: Annotated[list[BackupGroup], Query(min_length=1)],
	format: Literal["json", "csv", "xlsx"] = "json",
	current_user: Account = Depends(get_current_admin_only),
	db: Session = Depends(get_db),
) -> Response:
	del current_user
	try:
		content, filename, media_type = BackupService(db).export(
			[group.value for group in groups], format
		)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=str(exc),
		) from exc
	return Response(
		content=content,
		media_type=media_type,
		headers={"Content-Disposition": f'attachment; filename="{filename}"'},
	)


@router.post(
	"/import",
	status_code=status.HTTP_200_OK,
	response_model=ActionResponse,
	responses={
		400: {"model": ErrorResponse},
		401: {"model": ErrorResponse},
		403: {"model": ErrorResponse},
		409: {"model": ErrorResponse},
		413: {"model": ErrorResponse},
		422: {"model": ErrorResponse},
	},
	summary="Import an admin backup",
)
async def import_admin_backup(
	file: UploadFile = File(...),
	format: Literal["json", "csv", "xlsx"] = "json",
	current_user: Account = Depends(get_current_admin_only),
	db: Session = Depends(get_db),
) -> ActionResponse:
	del current_user
	content = await file.read(MAX_BACKUP_SIZE + 1)
	if len(content) > MAX_BACKUP_SIZE:
		raise HTTPException(
			status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
			detail=BackupError.FILE_TOO_LARGE,
		)
	if not content:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=BackupError.FILE_EMPTY)

	try:
		BackupService(db).import_backup(content, format)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=BackupError.INVALID_BACKUP,
		) from exc
	except SQLAlchemyError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail={
				"message": BackupError.DATA_CONFLICT,
				"details": _database_conflict_details(exc),
			},
		) from exc

	return ActionResponse(message=BackupSuccess.IMPORTED)
