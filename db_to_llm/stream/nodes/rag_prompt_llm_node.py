# 이 파일은 RAG 검색 컨텍스트를 포함한 프롬프트로 SQL을 생성하는 노드다.
# 조회 결과를 텍스트 블록으로 변환해 rag_query_generation_prompt 템플릿에 주입한다.
# SQL 생성 로직은 llm/prompt 서비스 계층을 호출해 노드 책임을 단순화한다.
# 컨텍스트가 비어도 프롬프트를 생성해 실패 대신 완화된 결과를 낼 수 있게 설계한다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.llm_service import generate_text
from db_to_llm.stream.services.prompt_service import build_rag_prompt_values, render_prompt
from db_to_llm.stream.services.rag_service import build_context_block

logger = get_logger(__name__)


def rag_prompt_llm_node(state: StreamGraphState) -> StreamGraphState:
    """
    RAG 컨텍스트를 포함해 SQL 초안을 생성한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: generated_sql이 반영된 상태 조각.
    """
    runtime = get_runtime(state)
    question = str(state.get("normalized_question") or state.get("question") or "").strip()
    retrieved_context = list(state.get("retrieved_context", []))

    try:
        context_block = build_context_block(retrieved_context)
        system_prompt = runtime.prompt_manager.get_prompt("default_system_prompt")
        user_prompt = render_prompt(
            prompt_manager=runtime.prompt_manager,
            prompt_key="rag_query_generation_prompt",
            values=build_rag_prompt_values(
                config=runtime.config,
                question=question,
                context_block=context_block,
            ),
        )
        generated_sql = generate_text(
            llm_client=runtime.llm_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
        )
    except Exception as error:
        logger.exception("rag_prompt_llm 노드 실패")
        return {
            "generated_sql": None,
            "errors": append_error(state, f"rag_prompt_llm_error: {error}"),
            "debug_trace": append_trace(state, "rag_prompt_llm_node:error"),
            "route_type": "rag_prompt_llm",
        }

    return {
        "generated_sql": generated_sql,
        "debug_trace": append_trace(state, "rag_prompt_llm_node"),
        "route_type": "rag_prompt_llm",
    }

