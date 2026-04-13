# 이 파일은 ChromaDB에서 관련 문서를 검색하는 RAG 검색 노드이다.
# RAG_ONLY, DB_THEN_RAG, RAG_THEN_GENERAL 경로에서 실행된다.
# DB_THEN_RAG 경로에서는 question + db_summary를 합쳐 더 풍부한 검색 쿼리를 사용한다.
# 검색 결과는 retrieved_contexts에 저장되어 final_answer_node에서 사용된다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.services.rag_service import retrieve_contexts

logger = get_logger(__name__)


def retrieve_rag_node(state: GraphState) -> GraphState:
    """
    사용자 질문(또는 질문+DB요약)으로 ChromaDB에서 관련 문서를 검색한다.

    입력 state 키: question, db_summary (DB_THEN_RAG 경로에서만 있음)
    출력 state 키: retrieved_contexts

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: retrieved_contexts가 추가된 상태.
    """
    question = state.get("question", "")
    db_summary = state.get("db_summary")
    query_type = state.get("query_type", "")

    # DB_THEN_RAG 경로: question + db_summary를 합쳐 검색 쿼리 확장
    if query_type == "DB_THEN_RAG" and db_summary:
        search_query = f"{question}\n\n[DB 조회 결과 요약]\n{db_summary}"
        logger.info(
            "retrieve_rag_node: DB_THEN_RAG 경로 - db_summary와 question을 합쳐 검색"
        )
    else:
        search_query = question

    logger.info("retrieve_rag_node 시작: query_length=%d", len(search_query))
    config = get_config(state)

    try:
        contexts = retrieve_contexts(query=search_query, config=config)
        logger.info("retrieve_rag_node 완료: result_count=%d", len(contexts))

        return {
            **state,
            "retrieved_contexts": contexts,
            "trace_logs": append_trace(
                state, f"retrieve_rag_node: result_count={len(contexts)}"
            ),
        }

    except Exception as error:
        logger.error("retrieve_rag_node 실패: %s", error)
        return {
            **state,
            "retrieved_contexts": [],
            "errors": append_error(state, f"retrieve_rag_node 실패: {error}"),
            "trace_logs": append_trace(state, "retrieve_rag_node: 실패"),
        }
