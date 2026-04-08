# 이 파일은 STREAM 결과 payload에 SQL 실행 결과를 선택적으로 결합하는 훅을 제공한다.
# main.py가 SQL 실행 세부 구현을 직접 알지 않도록 통합 지점을 분리했다.
# SQL 실행이 꺼진 경우 기존 생성 결과를 그대로 반환해 하위 호환을 유지한다.
# SQL 실행이 켜진 경우 공통 SQL 실행 서비스를 호출해 execution_result를 추가한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def append_sql_execution_result(
    result_payload: dict[str, Any],
    config_path: Path,
    execute_sql: bool,
) -> dict[str, Any]:
    """
    역할:
        SQL 실행 옵션이 켜진 경우 생성된 SQL을 MSSQL에서 실행하고 결과 payload를 추가한다.
        실행 중 예외가 발생하면 로그를 남기고 payload에 오류 정보를 기록한 뒤 계속 진행한다.

    Args:
        result_payload: `StreamResult.to_dict()` 결과 딕셔너리.
        config_path: MSSQL 설정이 포함된 config.yaml 절대 경로.
        execute_sql: SQL 실행 여부 플래그.

    Returns:
        dict[str, Any]: 실행 성공 시 `execution_result`, 실패 시 `execution_error`가 반영된 결과 딕셔너리.
    """
    if not execute_sql:
        logger.info("SQL 실행 미사용(--execute-sql 미지정): 생성 결과만 출력합니다.")
        return result_payload

    generated_sql = str(result_payload.get("query", "")).strip()
    if not generated_sql:
        error_message = "SQL 실행을 요청했지만 생성된 query가 비어 있습니다."
        logger.error(error_message)
        result_payload["execution_error"] = error_message
        result_payload["execution_result"] = {"columns": [], "row_count": 0, "rows": []}
        return result_payload

    logger.info("생성 SQL 실행 시작")
    try:
        from Root_Stream.services.sql.sql_execution_integration import (
            build_execution_payload,
            run_generated_sql_with_config_path,
        )
    except ModuleNotFoundError as error:
        error_message = (
            "SQL 실행 의존성이 없습니다. requirements 설치 후 다시 실행하세요. "
            "(예: pandas, SQLAlchemy, pyodbc)"
        )
        logger.exception(error_message)
        result_payload["execution_error"] = f"{error_message} | detail={error}"
        result_payload["execution_result"] = {"columns": [], "row_count": 0, "rows": []}
        return result_payload

    try:
        dataframe = run_generated_sql_with_config_path(
            generated_sql=generated_sql,
            config_path=config_path,
        )
        result_payload["execution_result"] = build_execution_payload(dataframe)
        logger.info("생성 SQL 실행 완료: row_count=%d", result_payload["execution_result"]["row_count"])
    except Exception as error:
        logger.exception("생성 SQL 실행 실패")
        result_payload["execution_error"] = str(error)
        result_payload["execution_result"] = {"columns": [], "row_count": 0, "rows": []}
    return result_payload
