# 이 파일은 DB/RAG가 필요 없는 일반 질문에 답변하는 노드이다.
# GENERAL, RAG_THEN_GENERAL 경로에서 실행된다.
# LLM에게 general_answer_prompt를 사용해 일반 지식 기반 답변을 생성한다.
# 생성된 답변은 final_answer_node로 전달되어 최종 응답으로 포장된다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.services.llm_service import generate_text
from src.db_to_llm.stream.services.prompt_service import get_prompt_manager

logger = get_logger(__name__)


def general_answer_node(state: GraphState) -> GraphState:
    """
    DB/RAG 없이 LLM 일반 지식으로 사용자 질문에 답변한다.

    입력 state 키: question
    출력 state 키: final_answer (중간 저장, final_answer_node에서 덮어씀)

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: general_answer가 저장된 상태.
    """
    question = state.get("question", "")
    logger.info("general_answer_node 시작: question=%s", question[:50])

    config = get_config(state)
    prompt_manager = get_prompt_manager(config)

    try:
        user_prompt = prompt_manager.render_prompt(
            "general_answer_prompt",
            values={"question": question},
        )
        system_prompt = "너는 친절하고 명확한 한국어 답변을 제공하는 어시스턴트다."

        answer = generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config,
            caller_name="general_answer_node",
        )

        logger.info("general_answer_node 완료: answer_length=%d", len(answer))

        return {
            **state,
            "final_answer": answer,  # final_answer_node가 최종 포장을 담당
            "trace_logs": append_trace(
                state, f"general_answer_node: answer_length={len(answer)}"
            ),
        }

    except Exception as error:
        logger.error("general_answer_node 실패: %s", error)
        return {
            **state,
            "final_answer": None,
            "errors": append_error(state, f"general_answer_node 실패: {error}"),
            "trace_logs": append_trace(state, "general_answer_node: 실패"),
        }
