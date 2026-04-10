# 이 파일은 schema/business 제약을 포함한 템플릿 프롬프트로 SQL을 생성하는 노드다.
# 기존 prompt_llm 모드 규칙(active_prompt, prompt values)을 그대로 재사용한다.
# 노드는 프롬프트 키 결정과 상태 업데이트만 담당하고 문자열 조합은 서비스에 위임한다.
# 생성 실패 시 오류를 상태에 누적해 이후 노드가 실패 원인을 참조할 수 있게 한다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.llm_service import generate_text
from db_to_llm.stream.services.prompt_service import build_prompt_values, render_prompt

logger = get_logger(__name__)


def prompt_llm_node(state: StreamGraphState) -> StreamGraphState:
    """
    템플릿 기반 prompt_llm 모드로 SQL 초안을 생성한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: generated_sql/prompt_key가 반영된 상태 조각.
    """
    runtime = get_runtime(state)
    question = str(state.get("normalized_question") or state.get("question") or "").strip()
    config = runtime.config
    prompt_key = str(config.get("prompts", {}).get("active_prompt", "query_generation_prompt"))

    try:
        system_prompt = runtime.prompt_manager.get_prompt("default_system_prompt")
        user_prompt = render_prompt(
            prompt_manager=runtime.prompt_manager,
            prompt_key=prompt_key,
            values=build_prompt_values(config=config, question=question),
        )
        generated_sql = generate_text(
            llm_client=runtime.llm_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
        )
    except Exception as error:
        logger.exception("prompt_llm 노드 실패")
        return {
            "generated_sql": None,
            "errors": append_error(state, f"prompt_llm_error: {error}"),
            "debug_trace": append_trace(state, "prompt_llm_node:error"),
            "route_type": "prompt_llm",
        }

    return {
        "generated_sql": generated_sql,
        "debug_trace": append_trace(state, "prompt_llm_node"),
        "route_type": "prompt_llm",
    }

