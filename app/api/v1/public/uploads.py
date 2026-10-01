from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_current_actor
from app.schemas.response import SuccessResponse
from app.schemas.upload import FileUploadResponse
from app.services.cdn_service import upload_file_to_cdn


router = APIRouter(
    prefix="/public/files",
    tags=["Files"],
)


@router.post(
    "/upload",
    response_model=SuccessResponse[FileUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to temporary CDN storage",
    dependencies=[Depends(get_current_actor)],
)
async def upload_file(
    file: UploadFile = File(...),
):
    result = await upload_file_to_cdn(file=file)

    return SuccessResponse(
        message="File uploaded successfully",
        data=FileUploadResponse(**result),
    )