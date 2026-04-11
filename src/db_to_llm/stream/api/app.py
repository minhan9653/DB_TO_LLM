# 이 파일은 FastAPI 앱의 진입점이다.
# 앱을 생성하고 라우터를 등록하며 헬스체크 엔드포인트를 제공한다.
# uvicorn으로 이 파일을 실행하면 API 서버가 시작된다.
# CLI와 API가 동일한 graph runner를 사용하도록 라우터를 통해 통합한다.

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db_to_llm.shared.logging.logger import get_logger, setup_logger
from src.db_to_llm.stream.api.routes import router

setup_logger()
logger = get_logger(__name__)

app = FastAPI(
    title="DB_TO_LLM API",
    description="자연어 질문을 SQL/RAG/GENERAL 경로로 처리하는 Planner 기반 API",
    version="2.0.0",
)

# CORS 설정 (개발 환경)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 쿼리 처리 라우터 등록
app.include_router(router, prefix="/api", tags=["query"])


@app.get("/health", summary="헬스체크")
async def health() -> dict[str, str]:
    """서버가 정상 동작 중인지 확인한다."""
    return {"status": "ok", "service": "db_to_llm"}


@app.get("/", summary="루트")
async def root() -> dict[str, str]:
    """API 기본 정보를 반환한다."""
    return {
        "service": "DB_TO_LLM API",
        "version": "2.0.0",
        "docs": "/docs",
    }
