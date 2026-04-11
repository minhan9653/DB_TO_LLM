# 이 파일은 FastAPI 라우터로 POST /query 엔드포인트를 구현한다.
# 요청을 받아 graph runner를 실행하고 결과를 QueryResponse로 반환한다.
# CLI와 API 모두 run_graph()를 공통으로 호출해 동일한 로직을 재사용한다.
# 오류 발생 시 HTTP 상태 코드와 함께 명확한 오류 메시지를 반환한다.

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.api.schemas import QueryRequest, QueryResponse
from src.db_to_llm.stream.graph.runner import run_graph

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="자연어 질문으로 DB/RAG/GENERAL 처리 실행",
    description=(
        "사용자의 자연어 질문을 Planner → LangGraph를 통해 처리한다. "
        "query_type에 따라 DB_ONLY, RAG_ONLY, GENERAL: 등 경로로 분기된다."
    ),
)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    POST /query: 질문을 받아 Planner → Graph 흐름을 실행하고 최종 답변을 반환한다.

    Args:
        request: question과 선택적 config_path를 담은 요청 스키마.

    Returns:
        QueryResponse: 최종 답변, SQL, DB 결과, RAG 결과, 오류 정보.

    Raises:
        HTTPException 500: 처리 중 예상치 못한 오류가 발생한 경우.
    """
    logger.info("POST /query 요청 수신: question=%s", request.question[:50])

    config_path = Path(request.config_path) if request.config_path else None

    try:
        result = run_graph(
            question=request.question,
            config_path=config_path,
        )
    except Exception as error:
        logger.exception("POST /query 처리 중 오류: %s", error)
        raise HTTPException(
            status_code=500,
            detail=f"질문 처리 중 오류가 발생했습니다: {error}",
        )

    logger.info(
        "POST /query 응답 전송: query_type=%s, answer_length=%d",
        result.get("query_type", ""),
        len(result.get("final_answer", "") or ""),
    )

    return QueryResponse(**result)
