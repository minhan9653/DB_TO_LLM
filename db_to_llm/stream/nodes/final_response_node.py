# 이 파일은 그래프의 마지막 노드로 최종 응답과 출력 payload를 구성한다.
# 기존 최종 답변 생성 로직을 재사용해 Planner/SQL/DB/RAG 정보를 종합한 응답을 만든다.
# API/CLI/Notebook이 같은 payload 구조를 공유하도록 단일 결과 포맷을 정의한다.
# LLM 실패 시에도 fallback 응답이 포함되도록 서비스 계층 결과를 그대로 반영한다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.final_response_service import generate_final_response

logger = get_logger(__name__)


def final_response_node(state: StreamGraphState) -> StreamGraphState:
    """
    그래프 최종 응답을 생성하고 response_payload를 구성한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: final_answer 및 response_payload가 포함된 상태 조각.
    """
    runtime = get_runtime(state)
    question = str(state.get("normalized_question") or state.get("question") or "").strip()
    if bool(state.get("skip_final_answer", False)):
        errors = list(state.get("errors", []))
        final_answer = str(state.get("generated_sql") or "")
        response_payload = {
            "question": question,
            "mode": state.get("route_type"),
            "query_type": state.get("query_type"),
            "planner_result": state.get("planner_result"),
            "generated_sql": state.get("generated_sql"),
            "sql_validation_result": state.get("sql_validation_result"),
            "execution_result": state.get("execution_result", {"columns": [], "row_count": 0, "rows": []}),
            "db_summary": state.get("db_summary"),
            "retrieved_context": state.get("retrieved_context", []),
            "final_answer": final_answer,
            "errors": errors,
            "debug_trace": append_trace(state, "final_response_node"),
        }
        return {
            "final_answer": final_answer,
            "errors": errors,
            "response_payload": response_payload,
            "debug_trace": response_payload["debug_trace"],
        }

    try:
        final_result = generate_final_response(
            question=question,
            planner_result=state.get("planner_result"),
            generated_sql=state.get("generated_sql"),
            db_result_summary=state.get("db_summary"),
            rag_docs=state.get("retrieved_context", []),
            config_path=runtime.config_path,
            errors=list(state.get("errors", [])),
        )
        final_answer = final_result.get("final_answer")
        errors = list(state.get("errors", [])) + list(final_result.get("errors", []))
    except Exception as error:
        logger.exception("최종 응답 생성 실패")
        final_answer = None
        errors = append_error(state, f"final_response_error: {error}")

    response_payload = {
        "question": question,
        "mode": state.get("route_type"),
        "query_type": state.get("query_type"),
        "planner_result": state.get("planner_result"),
        "generated_sql": state.get("generated_sql"),
        "sql_validation_result": state.get("sql_validation_result"),
        "execution_result": state.get("execution_result", {"columns": [], "row_count": 0, "rows": []}),
        "db_summary": state.get("db_summary"),
        "retrieved_context": state.get("retrieved_context", []),
        "final_answer": final_answer,
        "errors": errors,
        "debug_trace": append_trace(state, "final_response_node"),
    }
    return {
        "final_answer": final_answer,
        "errors": errors,
        "response_payload": response_payload,
        "debug_trace": response_payload["debug_trace"],
    }
