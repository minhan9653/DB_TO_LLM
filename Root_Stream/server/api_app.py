# 이 파일은 STREAM 서버의 FastAPI 앱 진입점입니다.
# 디버그 환경에서 브레이크포인트를 쉽게 걸 수 있도록 앱 구성을 단순화했습니다.
# 실제 질의 생성은 routes -> services 계층으로 위임됩니다.
# 기존 CLI 실행 방식과 완전히 분리되어 동작합니다.

from __future__ import annotations

from fastapi import FastAPI

from Root_Stream.server.routes import router as query_router
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="DB_TO_LLM STREAM API",
    version="0.1.0",
    description="STREAM SQL 생성 서버 API",
)
app.include_router(query_router)


@app.get("/health")
def health() -> dict[str, str]:
    """
    서버 동작 여부를 빠르게 확인하는 헬스체크 엔드포인트입니다.
    """
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    """
    서버 시작 시점 로그를 남겨 디버그 상태를 확인합니다.
    """
    logger.info("STREAM FastAPI 서버 시작")

