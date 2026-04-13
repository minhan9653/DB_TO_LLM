# 이 파일은 스키마 정보와 사용자 질문을 기반으로 SQL을 생성하는 노드이다.
# DB_ONLY, DB_THEN_RAG, DB_THEN_GENERAL 경로에서 실행된다.
# RAG_ONLY 경로에서는 rag_query_generation_prompt를 사용해 검색 결과를 활용한다.
# 생성된 SQL은 generated_sql에 저장되고 validate_sql_node로 전달된다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.services.llm_service import generate_text
from src.db_to_llm.stream.services.prompt_service import (
    build_sql_prompt_values,
    get_prompt_manager,
)

logger = get_logger(__name__)


def generate_sql_node(state: GraphState) -> GraphState:
    """
    사용자 질문과 스키마 정보를 사용해 SQL을 생성하고 state에 저장한다.

    입력 state 키: question, query_type
    출력 state 키: generated_sql, trace_logs, errors

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: generated_sql이 추가된 상태.
    """
    question = state.get("question", "")
    query_type = state.get("query_type", "DB_ONLY")
    logger.info("generate_sql_node 시작: question=%s, query_type=%s", question[:40], query_type)

    config = get_config(state)
    prompt_manager = get_prompt_manager(config)

    # 프롬프트 키 선택: RAG 검색 결과가 있으면 rag 버전 사용
    retrieved_contexts = state.get("retrieved_contexts", [])
    if retrieved_contexts:
        prompt_key = "rag_query_generation_prompt"
        from src.db_to_llm.stream.services.rag_service import build_context_block
        context_block = build_context_block(retrieved_contexts)
        from src.db_to_llm.stream.services.prompt_service import build_rag_prompt_values
        prompt_values = build_rag_prompt_values(question, config, context_block)
    else:
        prompt_key = "query_generation_prompt"
        prompt_values = build_sql_prompt_values(question, config)

    try:
        user_prompt = prompt_manager.render_prompt(prompt_key, values=prompt_values)
        system_prompt = (
            "너는 MSSQL 전용 SQL 생성 전문가다. SQL 본문만 반환하라. "
            "설명, 주석, 코드블록을 포함하지 말라."
        )

        generated_sql = generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config,
            caller_name="generate_sql_node",
        )

        logger.info("generate_sql_node 완료: sql_length=%d", len(generated_sql))

        return {
            **state,
            "generated_sql": generated_sql,
            "trace_logs": append_trace(
                state, f"generate_sql_node: sql_length={len(generated_sql)}"
            ),
        }

    except Exception as error:
        logger.error("generate_sql_node 실패: %s", error)
        return {
            **state,
            "generated_sql": None,
            "errors": append_error(state, f"generate_sql_node 실패: {error}"),
            "trace_logs": append_trace(state, "generate_sql_node: 실패"),
        }
