# 이 파일은 LangGraph 그래프를 실행하는 진입점 함수를 담는다.
# builder.py에서 만든 그래프에 초기 상태를 넣어 실행하고 최종 결과를 반환한다.
# API 서버와 CLI가 모두 이 함수를 호출하므로 중복 코드가 없다.
# 설정 로드와 로깅 초기화도 이 함수에서 한 번만 수행한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db_to_llm.shared.config.config_loader import load_config
from src.db_to_llm.shared.logging.logger import get_logger, setup_logger
from src.db_to_llm.stream.graph.builder import build_graph
from src.db_to_llm.stream.graph.state import GraphState

logger = get_logger(__name__)


def run_graph(
    question: str,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    사용자 질문을 받아 Planner → Graph → 최종 답변 전 흐름을 실행한다.

    Args:
        question: 사용자가 입력한 자연어 질문.
        config_path: 설정 파일 경로. None이면 config/config.yaml을 사용한다.

    Returns:
        dict: 그래프 실행 결과.
              final_answer, query_type, generated_sql, db_rows, retrieved_contexts,
              errors, trace_logs 필드를 포함한다.
    """
    # 설정 및 로깅 초기화
    config = load_config(config_path)
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = config.get("logging", {}).get("log_file")
    log_file_path = Path(log_file) if log_file else None
    setup_logger(log_level=log_level, log_file_path=log_file_path)

    logger.info("Graph 실행 시작: question=%s", question[:50])

    # 초기 상태 구성
    initial_state: GraphState = {
        "question": question,
        "config_path": str(config_path) if config_path else "",
        "errors": [],
        "trace_logs": [],
    }

    # 그래프 빌드 및 실행
    compiled_graph = build_graph()

    try:
        final_state: GraphState = compiled_graph.invoke(
            initial_state,
            config={"configurable": {"config_data": config}},
        )
    except Exception:
        logger.exception("Graph 실행 중 오류 발생")
        raise

    logger.info(
        "Graph 실행 완료: query_type=%s, final_answer_length=%d",
        final_state.get("query_type", ""),
        len(final_state.get("final_answer", "") or ""),
    )

    return _extract_result(final_state)


def _extract_result(state: GraphState) -> dict[str, Any]:
    """GraphState에서 최종 결과 dict를 추출한다."""
    return {
        "question": state.get("question", ""),
        "query_type": state.get("query_type", ""),
        "planner_result": state.get("planner_result", {}),
        "generated_sql": state.get("generated_sql"),
        "validated_sql": state.get("validated_sql"),
        "sql_validation_passed": state.get("sql_validation_passed"),
        "sql_validation_error": state.get("sql_validation_error"),
        "db_rows": state.get("db_rows", []),
        "db_columns": state.get("db_columns", []),
        "db_row_count": state.get("db_row_count", 0),
        "db_summary": state.get("db_summary"),
        "retrieved_contexts": state.get("retrieved_contexts", []),
        "final_answer": state.get("final_answer"),
        "errors": state.get("errors", []),
        "trace_logs": state.get("trace_logs", []),
    }
