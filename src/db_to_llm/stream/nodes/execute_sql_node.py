# 이 파일은 검증된 SQL을 실제 DB에서 실행하는 노드이다.
# validated_sql이 없거나 검증에 실패한 경우 실행을 건너뛴다.
# 실행 결과(rows, columns, row_count)를 state에 저장해 summarize_db_node로 전달한다.
# DB 접속 오류나 쿼리 실패 시 오류를 기록하고 흐름을 계속 진행한다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.services.sql_service import execute_sql

logger = get_logger(__name__)


def execute_sql_node(state: GraphState) -> GraphState:
    """
    validated_sql을 DB에서 실행하고 결과를 state에 저장한다.

    입력 state 키: validated_sql, sql_validation_passed
    출력 state 키: db_rows, db_columns, db_row_count

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: DB 실행 결과가 추가된 상태.
    """
    validated_sql = state.get("validated_sql", "")
    validation_passed = state.get("sql_validation_passed", False)

    # 검증 실패 시 DB 실행 스킵
    if not validation_passed or not validated_sql:
        logger.warning("execute_sql_node: SQL 검증이 통과되지 않아 DB 실행을 건너뜁니다.")
        return {
            **state,
            "db_rows": [],
            "db_columns": [],
            "db_row_count": 0,
            "trace_logs": append_trace(state, "execute_sql_node: 검증 실패로 스킵"),
        }

    logger.info("execute_sql_node 시작: sql_length=%d", len(validated_sql))
    config = get_config(state)

    try:
        result = execute_sql(validated_sql=validated_sql, config=config)
        row_count = result["row_count"]
        logger.info("execute_sql_node 완료: row_count=%d", row_count)

        return {
            **state,
            "db_rows": result["rows"],
            "db_columns": result["columns"],
            "db_row_count": row_count,
            "trace_logs": append_trace(state, f"execute_sql_node: row_count={row_count}"),
        }

    except Exception as error:
        logger.error("execute_sql_node 실패: %s", error)
        return {
            **state,
            "db_rows": [],
            "db_columns": [],
            "db_row_count": 0,
            "errors": append_error(state, f"execute_sql_node 실패: {error}"),
            "trace_logs": append_trace(state, "execute_sql_node: DB 실행 실패"),
        }
