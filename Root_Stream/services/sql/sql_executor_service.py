# 이 파일은 생성된 SQL을 안전하게 실행하는 공통 실행 서비스를 제공한다.
# 내부에서 SQL Guard 검증 후 MSSQL 클라이언트를 호출해 조회 결과를 반환한다.
# 기존 SQL 생성 단계와 분리된 독립 레이어로 동작하며 Notebook/CLI에서 재사용된다.
# 설정은 config.yaml에서 읽고 max_rows 제한으로 과도한 조회를 방지한다.

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd

from Root_Stream.services.sql.mssql_client import MssqlClient, MssqlConnectionConfig
from Root_Stream.services.sql.sql_guard import SqlGuard
from Root_Stream.utils.config_loader import load_config
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class SqlExecutorService:
    """SQL Guard + MSSQL 실행을 통합한 서비스."""

    def __init__(self, sql_guard: SqlGuard, mssql_client: MssqlClient, max_rows: int = 1000) -> None:
        """실행 서비스 의존성을 주입받아 초기화한다."""
        self.sql_guard = sql_guard
        self.mssql_client = mssql_client
        self.max_rows = max(1, int(max_rows))

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "SqlExecutorService":
        """
        역할:
            config 값을 기반으로 SQL 실행 서비스 인스턴스를 생성한다.

        Args:
            config (dict[str, Any]):
                역할: DB 접속 정보와 SQL 실행 제약 설정을 읽기 위한 입력이다.
                값: `load_config()` 결과 딕셔너리 객체가 전달된다.
                전달 출처: CLI/Notebook/서비스 호출부에서 공통 config를 전달한다.
                주의사항: database.type, database.password, sql.max_rows 등 필수값 누락 시 예외가 발생한다.

        Returns:
            SqlExecutorService: SQL 검증과 실행을 동시에 수행하는 서비스 인스턴스를 반환한다.

        Raises:
            ValueError: database 또는 sql 설정이 잘못된 경우 발생한다.
        """
        sql_config = config.get("sql", {})
        if not isinstance(sql_config, dict):
            raise ValueError("sql 설정이 dict 형식이 아닙니다.")

        allow_only_select = bool(sql_config.get("allow_only_select", True))
        max_rows = int(sql_config.get("max_rows", 1000))
        connection_config = MssqlConnectionConfig.from_config(config)

        sql_guard = SqlGuard(allow_only_select=allow_only_select)
        mssql_client = MssqlClient(connection_config=connection_config)
        logger.info("SQL 실행 서비스 생성 완료: allow_only_select=%s, max_rows=%d", allow_only_select, max_rows)
        return cls(sql_guard=sql_guard, mssql_client=mssql_client, max_rows=max_rows)

    def run_query(self, sql: str) -> pd.DataFrame:
        """
        역할:
            생성된 SQL 문자열을 검증 후 MSSQL에 실행하고 최대 행 제한을 적용해 반환한다.

        Args:
            sql (str):
                역할: 상위 SQL 생성 단계에서 만들어진 SQL 문자열이다.
                값: 문자열 SQL 본문이 들어온다.
                전달 출처: STREAM 결과(query) 또는 테스트 코드에서 전달된다.
                주의사항: 본 함수는 조회용 SQL만 실행 가능하며 금지 키워드 포함 시 즉시 실패한다.

        Returns:
            pd.DataFrame: SQL 실행 결과 DataFrame(최대 max_rows 제한 적용)을 반환한다.

        Raises:
            ValueError: SQL Guard 검증 실패 시 발생한다.
            RuntimeError: MSSQL 연결/실행 실패 시 발생한다.
        """
        logger.info("SQL 실행 요청 수신")
        validated_sql = self.sql_guard.validate_query_sql(sql)
        logger.info("MSSQL 조회 실행 시작")
        dataframe = self.mssql_client.execute_query(validated_sql)
        limited_dataframe = self._apply_max_rows(dataframe)
        logger.info("SQL 실행 완료: row_count=%d", len(limited_dataframe))
        return limited_dataframe

    def run_query_as_rows(self, sql: str) -> list[dict[str, Any]]:
        """
        역할:
            SQL 실행 결과를 list[dict] 구조로 변환해 반환한다.

        Args:
            sql (str):
                역할: 실행 대상 SQL 문자열이다.
                값: 조회용 단일 SQL 텍스트가 전달된다.
                전달 출처: Notebook/서비스/후속 API 포맷터에서 전달된다.
                주의사항: 내부적으로 run_query를 호출하므로 동일한 검증/제약이 적용된다.

        Returns:
            list[dict[str, Any]]: 조회 결과를 JSON 직렬화 친화적인 행 리스트로 반환한다.

        Raises:
            ValueError: SQL Guard 검증 실패 시 발생한다.
            RuntimeError: MSSQL 실행 실패 시 발생한다.
        """
        dataframe = self.run_query(sql)
        normalized_dataframe = dataframe.where(pd.notnull(dataframe), None)
        return cast(list[dict[str, Any]], normalized_dataframe.to_dict(orient="records"))

    def close(self) -> None:
        """MSSQL 클라이언트 자원을 해제한다."""
        self.mssql_client.close()

    def _apply_max_rows(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """설정된 최대 행 수를 초과하면 결과를 잘라 반환한다."""
        if len(dataframe) <= self.max_rows:
            return dataframe
        logger.warning("조회 결과가 max_rows를 초과해 상위 %d건만 반환합니다.", self.max_rows)
        return dataframe.head(self.max_rows).copy()


def create_sql_executor_from_config_path(config_path: Path) -> SqlExecutorService:
    """
    역할:
        config 파일 경로를 받아 SQL 실행 서비스를 생성한다.

    Args:
        config_path (Path):
            역할: SQL 실행 관련 설정을 읽을 config 파일 경로다.
            값: `Root_Stream/config/config.yaml` 기준 Path 객체가 들어온다.
            전달 출처: Notebook/CLI/테스트 유틸에서 전달된다.
            주의사항: 잘못된 경로를 전달하면 config 로딩 단계에서 즉시 실패한다.

    Returns:
        SqlExecutorService: config 기반으로 초기화된 SQL 실행 서비스 인스턴스를 반환한다.

    Raises:
        FileNotFoundError: config 파일이 없으면 발생한다.
        ValueError: database/sql 설정이 잘못되면 발생한다.
    """
    config = load_config(config_path=config_path)
    return SqlExecutorService.from_config(config=config)
