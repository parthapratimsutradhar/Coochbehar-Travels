from fastapi import APIRouter, File, Query, UploadFile, status

from app.schemas.upload import FileUploadResponse
from app.services.cloudinary_service import upload_file_to_cloudinary


router = APIRouter(
    prefix="/files",
    tags=["Files"],
)


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to Cloudinary",
)
async def upload_file(
    sub_folder: str = Query(
        ...,
        min_length=1,
        description="Sub-folder under Coochbehar-travels",
    ),
    file: UploadFile = File(...),
):
    result = await upload_file_to_cloudinary(file=file, sub_folder=sub_folder)
    return FileUploadResponse(
        url=result["secure_url"],
        public_id=result["public_id"],
        folder=result["folder"],
        resource_type=result["resource_type"],
        format=result.get("format"),
        bytes=result.get("bytes"),
    )
