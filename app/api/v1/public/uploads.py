from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor
from app.core.config import settings
from app.db.database import get_db
from app.schemas.response import SuccessResponse
from app.schemas.upload import FileUploadResponse
from app.services.cdn_service import enforce_upload_rate_limit, upload_file_to_cdn
from app.services.client_ip_service import get_client_ip



router = APIRouter(
    prefix="/public/files",
    tags=["Files"],
)


@router.post(
    "/upload",
    response_model=SuccessResponse[FileUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to temporary CDN storage",
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    actor=Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    enforce_upload_rate_limit(db, actor, client_ip)
    result = await upload_file_to_cdn(file=file)
    result["url"] = f"{settings.CDN_BASE_URL.rstrip('/')}/{result['path'].lstrip('/')}"

    return SuccessResponse(
        message="File uploaded successfully",
        data=FileUploadResponse(**result),
    )