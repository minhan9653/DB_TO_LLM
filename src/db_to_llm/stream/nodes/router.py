# 이 파일은 planner_node 이후 query_type을 보고 다음 노드를 결정하는 라우터이다.
# 조건 분기 함수로 LangGraph의 add_conditional_edges()에 등록된다.
# DB가 필요하면 generate_sql_node, RAG만이면 retrieve_rag_node, 나머지는 general_answer_node로 보낸다.
# builder.py의 _route_after_db()와 함께 전체 분기 흐름을 제어한다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState

logger = get_logger(__name__)

# query_type → 다음 노드 이름 매핑
# DB가 포함된 모든 경로는 우선 generate_sql_node로 이동
_ROUTE_MAP: dict[str, str] = {
    "DB_ONLY": "generate_sql_node",
    "DB_THEN_RAG": "generate_sql_node",
    "DB_THEN_GENERAL": "generate_sql_node",
    "RAG_ONLY": "retrieve_rag_node",
    "RAG_THEN_GENERAL": "retrieve_rag_node",
    "GENERAL": "general_answer_node",
}


def route_by_query_type(state: GraphState) -> str:
    """
    state의 query_type 값을 보고 다음 노드 이름을 반환한다.
    LangGraph의 add_conditional_edges() 라우팅 함수로 사용된다.

    Args:
        state: planner_node 이후의 그래프 실행 상태.

    Returns:
        str: 다음 노드 이름. graph builder의 conditional_edges 매핑 키와 일치해야 한다.
    """
    query_type = state.get("query_type", "GENERAL").upper()
    next_node = _ROUTE_MAP.get(query_type, "general_answer_node")

    logger.info("router: query_type=%s → next_node=%s", query_type, next_node)
    return next_node
