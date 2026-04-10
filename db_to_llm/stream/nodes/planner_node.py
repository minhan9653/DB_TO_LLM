# 이 파일은 Planner를 호출해 질문 분류(query_type)와 단계 정보를 상태에 기록하는 노드다.
# Planner 구현은 기존 PlannerService를 재사용하고 노드는 오케스트레이션에만 집중한다.
# 라우팅에 필요한 최소 필드(query_type/steps/reasoning)를 표준 상태 키로 정리한다.
# Planner 실패 시 errors/debug_trace를 업데이트하고 예외를 다시 올려 실패를 명확히 드러낸다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.planner.services.planner_adapter import run_planner
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime

logger = get_logger(__name__)


def planner_node(state: StreamGraphState) -> StreamGraphState:
    """
    Planner를 실행해 계획 결과를 상태에 반영한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: planner 결과가 반영된 상태 조각.
    """
    runtime = get_runtime(state)
    question = str(state.get("normalized_question") or state.get("question") or "").strip()
    try:
        planner_output = run_planner(question=question, config_path=runtime.config_path)
    except Exception as error:
        logger.exception("planner 노드 실패")
        return {
            "errors": append_error(state, f"planner_error: {error}"),
            "debug_trace": append_trace(state, "planner_node:error"),
            "query_type": "GENERAL",
            "planner_result": {"is_composite": False, "query_type": "GENERAL", "steps": []},
            "planner_steps": [],
        }

    planner_result = planner_output["planner_result"]
    return {
        "planner_raw": planner_output["planner_raw"],
        "planner_result": planner_result,
        "query_type": planner_output["query_type"],
        "reasoning_summary": planner_output["reasoning_summary"],
        "planner_steps": list(planner_result.get("steps", [])),
        "debug_trace": append_trace(state, "planner_node"),
    }

