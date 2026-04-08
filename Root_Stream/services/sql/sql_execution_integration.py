# 이 파일은 기존 SQL 생성 결과를 SQL 실행 서비스에 연결하는 예시 함수를 제공한다.
# 기존 오케스트레이터 흐름을 직접 수정하지 않고 선택적으로 붙일 수 있게 분리했다.
# 상위 코드에서 query 문자열 또는 StreamResult를 전달하면 동일한 실행 경로를 탄다.
# Notebook/CLI/테스트에서 공통 연결 포인트로 재사용할 수 있도록 단순화했다.

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from Root_Stream.services.sql.sql_executor_service import SqlExecutorService, create_sql_executor_from_config_path
from Root_Stream.stream.models import StreamResult
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def run_generated_sql_with_executor(generated_sql: str, executor: SqlExecutorService) -> pd.DataFrame:
    """
    역할:
        이미 생성된 SQL 문자열을 전달받아 실행 서비스로 조회 결과를 반환한다.

    Args:
        generated_sql (str):
            역할: 상위 SQL 생성 단계에서 만들어진 SQL 문자열이다.
            값: SELECT 또는 WITH 기반 단일 SQL 문자열이 전달된다.
            전달 출처: STREAM 결과(query) 또는 실험 코드에서 전달된다.
            주의사항: 실제 실행 전 guard 검증이 수행되므로 금지 구문은 예외로 차단된다.
        executor (SqlExecutorService):
            역할: SQL 검증/실행을 담당하는 공통 서비스 인스턴스다.
            값: config 기반으로 초기화된 SqlExecutorService 객체가 전달된다.
            전달 출처: Notebook 또는 호출 모듈에서 생성해 전달한다.
            주의사항: 실행 후 필요하면 close()를 호출해 연결 자원을 정리해야 한다.

    Returns:
        pd.DataFrame: 실행 결과 DataFrame을 반환한다.

    Raises:
        ValueError: SQL Guard 검증 실패 시 발생한다.
        RuntimeError: MSSQL 실행 실패 시 발생한다.
    """
    logger.info("생성 SQL 실행 연결 시작")
    dataframe = executor.run_query(generated_sql)
    logger.info("생성 SQL 실행 연결 완료: row_count=%d", len(dataframe))
    return dataframe


def run_stream_result_query(stream_result: StreamResult, executor: SqlExecutorService) -> pd.DataFrame:
    """
    역할:
        StreamResult.query를 SQL 실행 서비스로 전달해 조회 결과를 반환한다.

    Args:
        stream_result (StreamResult):
            역할: 기존 STREAM 단계의 표준 결과 모델이다.
            값: query 문자열을 포함한 StreamResult 객체가 전달된다.
            전달 출처: StreamOrchestrator.run() 결과가 전달된다.
            주의사항: query가 빈 문자열이면 SQL Guard 단계에서 예외가 발생한다.
        executor (SqlExecutorService):
            역할: SQL 실행 공통 서비스 인스턴스다.
            값: SqlExecutorService 객체가 전달된다.
            전달 출처: Notebook/CLI 통합 코드에서 생성해 전달한다.
            주의사항: 실행 후 서비스 close() 호출로 자원 해제가 필요하다.

    Returns:
        pd.DataFrame: stream_result.query 실행 결과를 반환한다.

    Raises:
        ValueError: stream_result.query 검증 실패 시 발생한다.
        RuntimeError: MSSQL 실행 실패 시 발생한다.
    """
    return run_generated_sql_with_executor(generated_sql=stream_result.query, executor=executor)


def run_generated_sql_with_config_path(generated_sql: str, config_path: Path) -> pd.DataFrame:
    """
    역할:
        config 파일 경로를 받아 SQL 실행 서비스를 생성하고 단일 SQL을 즉시 실행한다.

    Args:
        generated_sql (str):
            역할: 실행 대상 SQL 문자열이다.
            값: 상위 단계에서 생성된 SQL 텍스트가 전달된다.
            전달 출처: STREAM 결과 또는 테스트 입력에서 전달된다.
            주의사항: 내부에서 guard 검증을 수행하므로 비조회 SQL은 실행되지 않는다.
        config_path (Path):
            역할: MSSQL 및 SQL 실행 설정을 읽을 config 경로다.
            값: `Root_Stream/config/config.yaml` 경로가 전달된다.
            전달 출처: Notebook/CLI 예시 코드에서 전달된다.
            주의사항: 잘못된 경로 또는 잘못된 설정이면 서비스 생성 단계에서 예외가 발생한다.

    Returns:
        pd.DataFrame: SQL 실행 결과 DataFrame을 반환한다.

    Raises:
        FileNotFoundError: config 파일이 없으면 발생한다.
        ValueError: config 또는 SQL 검증 실패 시 발생한다.
        RuntimeError: MSSQL 실행 실패 시 발생한다.
    """
    executor = create_sql_executor_from_config_path(config_path=config_path)
    try:
        return run_generated_sql_with_executor(generated_sql=generated_sql, executor=executor)
    finally:
        executor.close()


def build_execution_payload(dataframe: pd.DataFrame) -> dict[str, Any]:
    """
    역할:
        SQL 실행 결과 DataFrame을 rows/columns 기반 표준 payload로 변환한다.

    Args:
        dataframe (pd.DataFrame):
            역할: SQL 실행 결과 DataFrame이다.
            값: 컬럼/행이 포함된 pandas DataFrame 객체가 전달된다.
            전달 출처: SqlExecutorService.run_query() 또는 통합 함수 결과가 전달된다.
            주의사항: NaN 값은 JSON 직렬화 불편을 줄이기 위해 None으로 정규화된다.

    Returns:
        dict[str, Any]: columns/row_count/rows 필드를 포함한 결과 딕셔너리를 반환한다.

    Raises:
        Exception: DataFrame 직렬화 변환 중 예외가 발생하면 전파된다.
    """
    normalized_dataframe = dataframe.where(pd.notnull(dataframe), None)
    rows = normalized_dataframe.to_dict(orient="records")
    return {
        "columns": list(normalized_dataframe.columns),
        "row_count": len(normalized_dataframe),
        "rows": rows,
    }
