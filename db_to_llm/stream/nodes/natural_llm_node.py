# 이 파일은 자연어 기반 LLM 호출로 SQL 초안을 생성하는 노드다.
# 복잡한 프롬프트 조합 없이 기본 시스템 프롬프트 + 질문만 사용한다.
# SQL 생성 결과는 generated_sql 상태 키로 저장해 이후 검증 노드가 재사용한다.
# 생성 실패 시 오류를 상태에 기록해 최종 응답 노드에서 원인을 함께 안내할 수 있다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.llm_service import generate_text

logger = get_logger(__name__)


def natural_llm_node(state: StreamGraphState) -> StreamGraphState:
    """
    자연어 LLM 모드로 SQL 초안을 생성한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: generated_sql이 반영된 상태 조각.
    """
    runtime = get_runtime(state)
    question = str(state.get("normalized_question") or state.get("question") or "").strip()

    try:
        system_prompt = runtime.prompt_manager.get_prompt("default_system_prompt")
        generated_sql = generate_text(
            llm_client=runtime.llm_client,
            system_prompt=system_prompt,
            user_prompt=question,
            temperature=0.0,
        )
    except Exception as error:
        logger.exception("natural_llm 노드 실패")
        return {
            "generated_sql": None,
            "errors": append_error(state, f"natural_llm_error: {error}"),
            "debug_trace": append_trace(state, "natural_llm_node:error"),
            "route_type": "natural_llm",
        }

    return {
        "generated_sql": generated_sql,
        "debug_trace": append_trace(state, "natural_llm_node"),
        "route_type": "natural_llm",
    }

