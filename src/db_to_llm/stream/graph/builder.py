# 이 파일은 LangGraph 노드들을 연결해 전체 실행 그래프를 조립하는 역할이다.
# START -> planner_node -> router 이후 query_type에 따라 경로가 분기된다.
# 노드 구현은 각 nodes/ 파일에 있고, 이 파일은 연결(edge) 설정만 담당한다.
# graph를 컴파일해 반환하므로 runner.py에서 곧바로 invoke()를 호출할 수 있다.

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.execute_sql_node import execute_sql_node
from src.db_to_llm.stream.nodes.final_answer_node import final_answer_node
from src.db_to_llm.stream.nodes.general_answer_node import general_answer_node
from src.db_to_llm.stream.nodes.generate_sql_node import generate_sql_node
from src.db_to_llm.stream.nodes.planner_node import planner_node
from src.db_to_llm.stream.nodes.retrieve_rag_node import retrieve_rag_node
from src.db_to_llm.stream.nodes.router import route_by_query_type
from src.db_to_llm.stream.nodes.summarize_db_node import summarize_db_node
from src.db_to_llm.stream.nodes.validate_sql_node import validate_sql_node


def build_graph() -> StateGraph:
    """
    Planner 중심 LangGraph 그래프를 조립하고 컴파일해 반환한다.

    그래프 흐름:
        START -> planner_node -> router
        DB_ONLY        -> generate_sql -> validate_sql -> execute_sql -> summarize_db -> final_answer
        RAG_ONLY       -> retrieve_rag -> final_answer
        GENERAL        -> general_answer -> final_answer
        DB_THEN_RAG    -> generate_sql -> validate_sql -> execute_sql -> summarize_db -> retrieve_rag -> final_answer
        DB_THEN_GENERAL-> generate_sql -> validate_sql -> execute_sql -> summarize_db -> final_answer
        RAG_THEN_GENERAL-> retrieve_rag -> final_answer

    Returns:
        CompiledGraph: invoke()를 바로 호출할 수 있는 컴파일된 그래프.
    """
    graph = StateGraph(GraphState)

    # ── 노드 등록 ────────────────────────────────────────
    graph.add_node("planner_node", planner_node)
    graph.add_node("generate_sql_node", generate_sql_node)
    graph.add_node("validate_sql_node", validate_sql_node)
    graph.add_node("execute_sql_node", execute_sql_node)
    graph.add_node("summarize_db_node", summarize_db_node)
    graph.add_node("retrieve_rag_node", retrieve_rag_node)
    graph.add_node("general_answer_node", general_answer_node)
    graph.add_node("final_answer_node", final_answer_node)

    # ── 진입점: START → planner ───────────────────────────
    graph.add_edge(START, "planner_node")

    # ── planner → router (조건 분기) ─────────────────────
    graph.add_conditional_edges(
        "planner_node",
        route_by_query_type,
        {
            "generate_sql_node": "generate_sql_node",
            "retrieve_rag_node": "retrieve_rag_node",
            "general_answer_node": "general_answer_node",
        },
    )

    # ── SQL 경로: generate → validate → execute → summarize ─
    graph.add_edge("generate_sql_node", "validate_sql_node")
    graph.add_edge("validate_sql_node", "execute_sql_node")
    graph.add_edge("execute_sql_node", "summarize_db_node")

    # ── summarize 이후 재분기: DB_THEN_RAG는 RAG로, 나머지는 final ─
    graph.add_conditional_edges(
        "summarize_db_node",
        _route_after_db,
        {
            "retrieve_rag_node": "retrieve_rag_node",
            "final_answer_node": "final_answer_node",
        },
    )

    # ── RAG 이후 → final_answer ───────────────────────────
    graph.add_edge("retrieve_rag_node", "final_answer_node")

    # ── general_answer → final_answer ────────────────────
    graph.add_edge("general_answer_node", "final_answer_node")

    # ── final_answer → END ───────────────────────────────
    graph.add_edge("final_answer_node", END)

    return graph.compile()


def _route_after_db(state: GraphState) -> str:
    """
    summarize_db_node 이후 query_type에 따라 다음 노드를 결정한다.

    - DB_THEN_RAG: RAG 검색도 필요하므로 retrieve_rag_node로 이동
    - 나머지(DB_ONLY, DB_THEN_GENERAL 등): 바로 final_answer_node로 이동
    """
    query_type = state.get("query_type", "DB_ONLY")
    if query_type == "DB_THEN_RAG":
        return "retrieve_rag_node"
    return "final_answer_node"
