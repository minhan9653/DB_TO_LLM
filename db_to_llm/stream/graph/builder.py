# 이 파일은 Stream 실행용 LangGraph를 구성하는 빌더 모듈이다.
# 노드 등록, 엣지 연결, 조건부 라우팅을 한 곳에 모아 흐름을 명확히 드러낸다.
# langgraph 미설치 환경에서는 fallback 그래프 구현으로 동일 인터페이스를 제공한다.
# CLI/API/Notebook은 이 빌더가 만든 단일 그래프 실행 경로를 공통으로 재사용한다.

from __future__ import annotations

from typing import Any

from db_to_llm.stream.graph.routes import route_after_sql_validation, route_by_plan
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.db_execute_node import db_execute_node
from db_to_llm.stream.nodes.final_response_node import final_response_node
from db_to_llm.stream.nodes.load_runtime_config_node import load_runtime_config_node
from db_to_llm.stream.nodes.natural_llm_node import natural_llm_node
from db_to_llm.stream.nodes.planner_node import planner_node
from db_to_llm.stream.nodes.prompt_llm_node import prompt_llm_node
from db_to_llm.stream.nodes.rag_prompt_llm_node import rag_prompt_llm_node
from db_to_llm.stream.nodes.rag_retrieve_node import rag_retrieve_node
from db_to_llm.stream.nodes.result_summary_node import result_summary_node
from db_to_llm.stream.nodes.sql_validation_node import sql_validation_node

try:
    from langgraph.graph import END, START, StateGraph
except Exception:
    from db_to_llm.stream.graph.fallback_graph import END, START, StateGraph


def build_stream_graph() -> Any:
    """
    Stream LangGraph를 생성하고 컴파일된 실행 객체를 반환한다.

    Returns:
        Any: `invoke(state)`를 지원하는 컴파일된 그래프 객체.
    """
    graph = StateGraph(StreamGraphState)

    graph.add_node("load_runtime_config_node", load_runtime_config_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("natural_llm_node", natural_llm_node)
    graph.add_node("prompt_llm_node", prompt_llm_node)
    graph.add_node("rag_retrieve_node", rag_retrieve_node)
    graph.add_node("rag_prompt_llm_node", rag_prompt_llm_node)
    graph.add_node("sql_validation_node", sql_validation_node)
    graph.add_node("db_execute_node", db_execute_node)
    graph.add_node("result_summary_node", result_summary_node)
    graph.add_node("final_response_node", final_response_node)

    graph.add_edge(START, "load_runtime_config_node")
    graph.add_edge("load_runtime_config_node", "planner_node")

    graph.add_conditional_edges(
        "planner_node",
        route_by_plan,
        {
            "natural_llm_node": "natural_llm_node",
            "prompt_llm_node": "prompt_llm_node",
            "rag_retrieve_node": "rag_retrieve_node",
        },
    )

    graph.add_edge("rag_retrieve_node", "rag_prompt_llm_node")

    graph.add_edge("natural_llm_node", "sql_validation_node")
    graph.add_edge("prompt_llm_node", "sql_validation_node")
    graph.add_edge("rag_prompt_llm_node", "sql_validation_node")

    graph.add_conditional_edges(
        "sql_validation_node",
        route_after_sql_validation,
        {
            "db_execute_node": "db_execute_node",
            "final_response_node": "final_response_node",
        },
    )
    graph.add_edge("db_execute_node", "result_summary_node")
    graph.add_edge("result_summary_node", "final_response_node")
    graph.add_edge("final_response_node", END)

    return graph.compile()

