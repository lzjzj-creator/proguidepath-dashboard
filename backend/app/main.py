import logging
import os
import shutil

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.resume_routes import router as resume_router
from app.db.connection import close_postgres_pool, using_postgres
from app.db.init_db import init_db


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)


def setup_database_file() -> None:
    """
    Zeabur 部署兼容：如果存在持久化 /data 目录，则优先把项目内初始
    SQLite 数据库同步过去。本地运行时如果无法写入 /data，会自动回退到
    RESUME_DB_PATH 或 backend/data/resume.db。
    """
    target_db_path = "/data/resume.db"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_db_path = os.path.join(base_dir, "data", "resume.db")

    try:
        os.makedirs(os.path.dirname(target_db_path), exist_ok=True)
    except Exception as e:
        print(f"无法创建 /data 目录，将使用本地数据库: {e}")
        return

    if os.path.exists(target_db_path):
        print("检测到持久化数据库文件")
        return

    if not os.path.exists(source_db_path):
        print(f"未找到初始数据库文件: {source_db_path}，将由 init_db 创建空表")
        return

    try:
        shutil.copy2(source_db_path, target_db_path)
        print(f"成功将初始数据库同步至: {target_db_path}")
    except Exception as e:
        print(f"数据库同步失败，将使用本地数据库: {e}")


def create_app() -> FastAPI:
    if not using_postgres():
        setup_database_file()

    app = FastAPI(title="Recruitment Matching API", version="2.0.0")

    raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    if raw_origins:
        origins = [item.strip() for item in raw_origins.split(",") if item.strip()]
        allow_credentials = True
    else:
        origins = ["*"]
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()
    app.include_router(resume_router, prefix="/api")

    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "service": "recruitment-matching-api"}

    @app.on_event("shutdown")
    def shutdown_database_pool() -> None:
        close_postgres_pool()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            content = {
                "stage": exc.detail.get("stage", "http_error"),
                "message": exc.detail.get("message", str(exc.detail.get("detail", "request failed"))),
                "detail": exc.detail.get("detail", exc.detail),
            }
        else:
            content = {
                "stage": "http_error",
                "message": str(exc.detail),
                "detail": exc.detail,
            }
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "stage": "request_validation_failed",
                "message": "请求参数校验失败",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        return JSONResponse(
            status_code=500,
            content={
                "stage": "internal_error",
                "message": "服务内部异常，请查看后端日志定位阶段",
                "detail": str(exc),
            },
        )

    return app


app = create_app()
