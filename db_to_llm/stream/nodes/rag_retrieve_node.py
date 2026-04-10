# 이 파일은 RAG 조회 전용 노드로 벡터 검색 결과를 상태에 저장한다.
# SQL 생성 노드와 조회 노드를 분리해 조건부 흐름 제어를 명확하게 유지한다.
# 검색 결과는 dict 리스트로 표준화해 프롬프트 조합과 최종 응답 노드에서 재사용한다.
# 조회 실패 시 에러를 누적하되 그래프를 중단하지 않고 다음 노드에서 복구 가능하게 둔다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.rag_service import retrieve_contexts

logger = get_logger(__name__)


def rag_retrieve_node(state: StreamGraphState) -> StreamGraphState:
    """
    질문 기반 RAG 조회를 수행한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: retrieved_context가 반영된 상태 조각.
    """
    runtime = get_runtime(state)
    question = str(state.get("normalized_question") or state.get("question") or "").strip()

    try:
        contexts = retrieve_contexts(
            config=runtime.config,
            project_root=runtime.project_root,
            question=question,
        )
    except Exception as error:
        logger.exception("rag_retrieve 노드 실패")
        return {
            "retrieved_context": [],
            "errors": append_error(state, f"rag_retrieve_error: {error}"),
            "debug_trace": append_trace(state, "rag_retrieve_node:error"),
            "route_type": "rag_prompt_llm",
        }

    return {
        "retrieved_context": contexts,
        "debug_trace": append_trace(state, "rag_retrieve_node"),
        "route_type": "rag_prompt_llm",
    }

