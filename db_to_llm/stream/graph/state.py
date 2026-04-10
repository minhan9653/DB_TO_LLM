# 이 파일은 LangGraph에서 노드 간에 공유할 상태 타입을 정의한다.
# 상태 필드를 명시해 노드 책임과 데이터 흐름을 초보자도 추적하기 쉽게 만든다.
# Planner 결과, 라우팅 결과, SQL/DB/RAG 중간 산출물을 한 곳에서 관리한다.
# 테스트에서도 동일 상태 스키마를 사용해 흐름 검증 기준을 통일한다.

from __future__ import annotations

from typing import Any, TypedDict

from db_to_llm.common.config.runtime_config import RuntimeServices


class StreamGraphState(TypedDict, total=False):
    """Stream 그래프 실행 상태."""

    question: str
    normalized_question: str
    mode: str
    execute_sql: bool
    skip_final_answer: bool
    config_path: str

    runtime: RuntimeServices
    runtime_config: dict[str, Any]

    planner_raw: str
    planner_result: dict[str, Any]
    query_type: str
    planner_steps: list[dict[str, Any]]
    reasoning_summary: str | None
    route_type: str

    retrieved_context: list[dict[str, Any]]
    rag_query: str | None

    generated_sql: str | None
    sql_validation_result: dict[str, Any]
    validated_sql: str | None

    execution_result: dict[str, Any]
    db_rows: list[dict[str, Any]]
    db_summary: dict[str, Any] | None

    final_answer: str | None
    errors: list[str]
    debug_trace: list[str]
