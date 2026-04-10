# 이 파일은 LangGraph 실행 진입점으로 CLI/API/Notebook에서 공통으로 사용된다.
# 입력을 초기 상태로 변환하고 그래프 invoke 결과를 표준 payload로 반환한다.
# 기존 query_service 호환을 위해 SQL 생성 중심 결과를 별도 helper로도 제공한다.
# 실행 실패 시 예외를 숨기지 않고 상위 호출자가 적절한 에러 응답을 만들 수 있게 둔다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from db_to_llm.stream.graph.builder import build_stream_graph
from db_to_llm.stream.graph.state import StreamGraphState


@dataclass
class GraphRunResult:
    """그래프 실행 표준 결과."""

    state: StreamGraphState
    payload: dict[str, Any]


def run_stream_graph(
    *,
    question: str,
    config_path: str | Path | None = None,
    mode: str = "auto",
    execute_sql: bool = False,
    skip_final_answer: bool = False,
) -> GraphRunResult:
    """
    Stream LangGraph를 실행하고 최종 payload를 반환한다.

    Args:
        question: 사용자 질문.
        config_path: stream config 경로.
        mode: 강제 라우팅 모드(auto/natural/prompt/rag_prompt).
        execute_sql: DB 실행 여부.

    Returns:
        GraphRunResult: 최종 상태와 응답 payload.
    """
    initial_state: StreamGraphState = {
        "question": question,
        "mode": mode,
        "execute_sql": execute_sql,
        "skip_final_answer": skip_final_answer,
        "config_path": str(config_path) if config_path else "",
        "errors": [],
        "debug_trace": [],
    }
    graph = build_stream_graph()
    final_state = graph.invoke(initial_state)
    payload = final_state.get("response_payload", {})
    return GraphRunResult(state=final_state, payload=payload)


def run_sql_generation_only(
    *,
    question: str,
    config_path: str | Path | None = None,
    mode: str = "prompt",
) -> dict[str, Any]:
    """
    API 호환을 위해 SQL 생성 중심 결과만 요약해 반환한다.

    Args:
        question: 사용자 질문.
        config_path: stream config 경로.
        mode: 강제 라우팅 모드.

    Returns:
        dict[str, Any]: success/mode/question/generated_query/errors 결과.
    """
    result = run_stream_graph(
        question=question,
        config_path=config_path,
        mode=mode,
        execute_sql=False,
        skip_final_answer=True,
    )
    generated_sql = result.payload.get("generated_sql")
    errors = list(result.payload.get("errors", []))
    success = bool(generated_sql) and not errors
    return {
        "success": success,
        "mode": result.payload.get("mode"),
        "question": question,
        "generated_query": generated_sql or "",
        "errors": errors,
    }
