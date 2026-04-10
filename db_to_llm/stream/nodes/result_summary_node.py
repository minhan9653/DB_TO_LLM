# 이 파일은 DB 실행 결과 payload를 요약하는 노드다.
# 요약 텍스트와 핵심 포인트를 분리해 최종 응답 노드에서 재사용할 수 있게 한다.
# DB 미실행/빈 결과인 경우에도 일관된 요약 구조를 반환해 후속 분기 단순화를 돕는다.
# 요약 로직은 서비스 계층 함수를 호출해 노드 책임을 최소화한다.

from __future__ import annotations

from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_trace
from db_to_llm.stream.services.sql_service import summarize_db_result


def result_summary_node(state: StreamGraphState) -> StreamGraphState:
    """
    execution_result를 요약해 db_summary 상태 필드에 기록한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: db_summary가 반영된 상태 조각.
    """
    execution_result = state.get("execution_result", {})
    if not isinstance(execution_result, dict):
        execution_result = {}
    return {
        "db_summary": summarize_db_result(execution_result),
        "debug_trace": append_trace(state, "result_summary_node"),
    }

