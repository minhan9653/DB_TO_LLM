# 이 파일은 STREAM 서버 API 라우트를 정의합니다.
# 라우트는 HTTP 요청/응답만 담당하고 비즈니스 로직은 services 로 위임합니다.
# 기존 CLI 흐름과 충돌하지 않도록 독립 엔드포인트만 추가합니다.
# 오류는 HTTP 상태코드로 명확하게 반환해 디버깅을 쉽게 합니다.

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from Root_Stream.server.models import QueryGenerateRequest, QueryGenerateResponse
from Root_Stream.services.query_service import generate_stream_query
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("/generate", response_model=QueryGenerateResponse)
def generate_query(payload: QueryGenerateRequest) -> QueryGenerateResponse:
    """
    질문과 mode 를 받아 SQL 생성 결과를 반환합니다.
    """
    try:
        result = generate_stream_query(
            question=payload.question,
            mode=payload.mode,
        )
        return QueryGenerateResponse(
            success=result.success,
            mode=result.mode,
            question=result.question,
            generated_query=result.generated_query,
        )
    except ValueError as error:
        logger.warning("요청 검증 실패: mode=%s, error=%s", payload.mode, str(error))
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("서버 SQL 생성 실패: mode=%s", payload.mode)
        raise HTTPException(
            status_code=500,
            detail="SQL 생성 중 서버 내부 오류가 발생했습니다.",
        ) from error

