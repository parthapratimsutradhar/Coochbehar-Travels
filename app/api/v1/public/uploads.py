from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import require_upload_key
from app.schemas.upload import FileUploadResponse
from app.services.cloudinary_service import upload_file_to_cloudinary


router = APIRouter(
    prefix="/public/files",
    tags=["Files"],
)


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to Cloudinary",
    dependencies=[Depends(require_upload_key)],
)
async def upload_file(
    file: UploadFile = File(...),
):
    result = await upload_file_to_cloudinary(file=file, sub_folder="temporary-uploads")
    return FileUploadResponse(
        url=result["secure_url"],
        public_id=result["public_id"],
        folder=result["folder"],
        resource_type=result["resource_type"],
        format=result.get("format"),
        bytes=result.get("bytes"),
    )
