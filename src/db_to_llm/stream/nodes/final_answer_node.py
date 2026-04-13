# 이 파일은 모든 경로의 마지막에서 최종 사용자 답변을 생성하는 노드이다.
# DB 요약, RAG 검색 결과, general 답변을 종합해 사용자 친화적인 답변을 만든다.
# 이미 final_answer가 있으면(GENERAL 경로) 그대로 사용하고 추가 LLM 호출을 하지 않는다.
# DB_THEN_RAG처럼 여러 결과를 합치는 경우에만 LLM을 추가 호출해 최종 답변을 구성한다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.services.llm_service import generate_text
from src.db_to_llm.stream.services.prompt_service import get_prompt_manager
from src.db_to_llm.stream.services.rag_service import build_context_block

logger = get_logger(__name__)


def final_answer_node(state: GraphState) -> GraphState:
    """
    모든 경로의 마지막에서 최종 사용자 답변을 생성해 final_answer에 저장한다.

    - GENERAL 경로: general_answer_node가 이미 final_answer를 채워뒀으므로 그대로 사용
    - DB_ONLY, DB_THEN_GENERAL: db_summary를 사용해 최종 답변 생성
    - RAG_ONLY, RAG_THEN_GENERAL: retrieved_contexts를 사용해 최종 답변 생성
    - DB_THEN_RAG: db_summary + retrieved_contexts를 모두 사용해 최종 답변 생성

    입력 state 키: question, db_summary, retrieved_contexts, final_answer (있을 수 있음)
    출력 state 키: final_answer

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: final_answer가 최종 확정된 상태.
    """
    question = state.get("question", "")
    query_type = state.get("query_type", "GENERAL")
    db_summary = state.get("db_summary")
    retrieved_contexts = state.get("retrieved_contexts", [])
    existing_answer = state.get("final_answer")

    logger.info("final_answer_node 시작: query_type=%s", query_type)

    # GENERAL 경로: 이미 답변이 준비됨
    if query_type == "GENERAL" and existing_answer:
        logger.info("final_answer_node: GENERAL 경로, 기존 답변 사용")
        return {
            **state,
            "final_answer": existing_answer,
            "trace_logs": append_trace(state, "final_answer_node: GENERAL 경로 완료"),
        }

    # 최소 자료가 없으면 오류 메시지 반환
    if not db_summary and not retrieved_contexts and not existing_answer:
        error_message = "답변을 생성하기 위한 정보가 충분하지 않습니다."
        logger.warning("final_answer_node: 정보 없음")
        return {
            **state,
            "final_answer": error_message,
            "errors": append_error(state, "final_answer_node: 답변 재료 없음"),
            "trace_logs": append_trace(state, "final_answer_node: 정보 없어 기본 메시지 반환"),
        }

    config = get_config(state)
    prompt_manager = get_prompt_manager(config)

    # 검색 결과 텍스트 블록 구성
    context_block = build_context_block(retrieved_contexts) if retrieved_contexts else ""

    try:
        user_prompt = prompt_manager.render_prompt(
            "final_answer_prompt",
            values={
                "question": question,
                "db_summary": db_summary or "",
                "retrieved_context": context_block,
            },
        )
        system_prompt = "너는 데이터 분석 결과와 문서 검색 결과를 바탕으로 한국어로 친절하게 답변하는 어시스턴트다."

        final_answer = generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config,
            caller_name="final_answer_node",
        )

        logger.info("final_answer_node 완료: answer_length=%d", len(final_answer))

        return {
            **state,
            "final_answer": final_answer,
            "trace_logs": append_trace(
                state, f"final_answer_node: answer_length={len(final_answer)}"
            ),
        }

    except Exception as error:
        logger.error("final_answer_node 실패: %s", error)
        # Fallback: db_summary 또는 context_block을 그대로 사용
        fallback = db_summary or context_block or "답변 생성에 실패했습니다."
        return {
            **state,
            "final_answer": fallback,
            "errors": append_error(state, f"final_answer_node 실패: {error}"),
            "trace_logs": append_trace(state, "final_answer_node: 실패, fallback 사용"),
        }
