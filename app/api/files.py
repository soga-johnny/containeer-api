from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import boto3
from botocore.exceptions import ClientError
from ..core.config import settings
from ..db.database import get_db
from ..db.models import File as FileModel, User
from typing import List
import uuid

router = APIRouter()

# S3クライアントの初期化
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.ply'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PLY files are allowed"
        )

    # ユニークなファイル名を生成
    file_key = f"{uuid.uuid4()}.ply"
    
    try:
        # S3にアップロード
        s3_client.upload_fileobj(
            file.file,
            settings.S3_BUCKET,
            file_key
        )

        # データベースに記録
        db_file = FileModel(
            filename=file.filename,
            s3_key=file_key,
            owner_id=current_user.id
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return {"id": db_file.id, "filename": db_file.filename}

    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{file_id}")
async def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    if file.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this file"
        )

    try:
        # S3から署名付きURLを生成
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.S3_BUCKET,
                'Key': file.s3_key
            },
            ExpiresIn=3600  # 1時間有効
        )
        return {"url": url}

    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    if file.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this file"
        )

    try:
        # S3からファイルを削除
        s3_client.delete_object(
            Bucket=settings.S3_BUCKET,
            Key=file.s3_key
        )

        # データベースから削除
        db.delete(file)
        db.commit()

        return {"message": "File deleted successfully"} 