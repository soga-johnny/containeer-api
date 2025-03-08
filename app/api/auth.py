from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
from ..core.config import settings
from ..core.security import create_access_token
from ..db.database import get_db
from ..db.models import User

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/login")
async def login(token: str, db: Session = Depends(get_db)):
    try:
        # Googleトークンの検証
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid issuer"
            )

        # ユーザーの取得または作成
        user = db.query(User).filter(User.google_id == idinfo['sub']).first()
        if not user:
            user = User(
                email=idinfo['email'],
                google_id=idinfo['sub'],
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # JWTトークンの生成
        access_token = create_access_token(
            data={"sub": user.email}
        )
        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.post("/logout")
async def logout():
    # クライアント側でトークンを破棄するため、サーバー側での特別な処理は不要
    return {"message": "Successfully logged out"} 