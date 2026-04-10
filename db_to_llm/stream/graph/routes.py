# 이 파일은 Planner 결과와 실행 옵션을 기반으로 그래프 라우팅을 결정한다.
# 분기 조건을 별도 모듈로 분리해 노드 구현에서 if/else 중복을 줄인다.
# 테스트에서는 이 함수들을 직접 검증해 라우팅 회귀를 빠르게 잡을 수 있다.
# mode 강제 지정과 Planner 기반 자동 라우팅을 동시에 지원한다.

from __future__ import annotations

from db_to_llm.common.types.planner import QUERY_TYPES_DB, QUERY_TYPES_RAG
from db_to_llm.stream.graph.state import StreamGraphState

ROUTE_NATURAL = "natural_llm_node"
ROUTE_PROMPT = "prompt_llm_node"
ROUTE_RAG_RETRIEVE = "rag_retrieve_node"


def route_by_plan(state: StreamGraphState) -> str:
    """
    Planner 결과(query_type)와 mode 옵션으로 SQL 생성 라우트를 결정한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        str: 다음 노드 이름.
    """
    explicit_mode = str(state.get("mode", "auto")).strip().lower()
    if explicit_mode in {"natural", "natural_llm"}:
        return ROUTE_NATURAL
    if explicit_mode in {"prompt", "prompt_llm"}:
        return ROUTE_PROMPT
    if explicit_mode in {"rag_prompt", "rag_prompt_llm"}:
        return ROUTE_RAG_RETRIEVE

    query_type = str(state.get("query_type", "")).strip().upper()
    if query_type in {"GENERAL"}:
        return ROUTE_NATURAL
    if query_type in {"DB_THEN_RAG", "RAG_ONLY", "RAG_THEN_GENERAL"}:
        return ROUTE_RAG_RETRIEVE
    if query_type in QUERY_TYPES_DB | QUERY_TYPES_RAG:
        return ROUTE_PROMPT
    return ROUTE_PROMPT


def route_after_sql_validation(state: StreamGraphState) -> str:
    """
    SQL 검증 이후 DB 실행 노드로 갈지 최종 응답 노드로 갈지 결정한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        str: 다음 노드 이름.
    """
    execute_sql = bool(state.get("execute_sql", False))
    validation_result = state.get("sql_validation_result", {})
    is_valid = bool(validation_result.get("is_valid", False)) if isinstance(validation_result, dict) else False
    validated_sql = str(state.get("validated_sql") or "").strip()
    if execute_sql and is_valid and validated_sql:
        return "db_execute_node"
    return "final_response_node"

