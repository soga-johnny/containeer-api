from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, files, users

app = FastAPI(title=settings.PROJECT_NAME)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Welcome to Containeer API"} 