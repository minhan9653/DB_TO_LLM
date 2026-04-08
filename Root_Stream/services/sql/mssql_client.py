# 이 파일은 MSSQL 연결 생성과 조회 실행을 담당하는 클라이언트를 제공한다.
# SQLAlchemy + pyodbc + pandas를 공통으로 사용해 Notebook/CLI 실행 방식을 통일한다.
# sql_executor_service가 이 모듈을 호출해 실제 DB 조회를 수행한다.
# 접속 정보는 config 기반으로 주입받고 민감값은 로그에 직접 출력하지 않는다.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MssqlConnectionConfig:
    """MSSQL 접속 설정 모델."""

    type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    driver: str
    encrypt: bool
    trust_server_certificate: bool
    timeout: int

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "MssqlConnectionConfig":
        """
        역할:
            config 딕셔너리에서 MSSQL 연결 설정을 읽어 타입 안정적인 모델로 변환한다.

        Args:
            config (dict[str, Any]):
                역할: 전체 STREAM 설정 데이터에서 database 항목을 읽기 위한 입력이다.
                값: `config.yaml` 로딩 결과 딕셔너리 형태가 들어온다.
                전달 출처: `load_config()` 호출 결과가 상위 서비스에서 전달된다.
                주의사항: 필수 key가 누락되면 즉시 `ValueError`를 발생시켜 실행을 중단한다.

        Returns:
            MssqlConnectionConfig: 검증된 MSSQL 접속 설정 모델을 반환한다.

        Raises:
            ValueError: database 설정 누락 또는 mssql 타입 불일치 시 발생한다.
        """
        database_config = config.get("database", {})
        if not isinstance(database_config, dict):
            raise ValueError("database 설정이 dict 형식이 아닙니다.")

        db_type = str(database_config.get("type", "mssql")).strip().lower()
        if db_type != "mssql":
            raise ValueError(f"database.type이 mssql이 아닙니다. current={db_type or 'empty'}")

        required_keys = ("host", "database", "username", "password")
        missing_keys = [key for key in required_keys if not str(database_config.get(key, "")).strip()]
        if missing_keys:
            missing_text = ", ".join(missing_keys)
            raise ValueError(f"database 설정 누락: {missing_text}")

        return cls(
            type=db_type,
            host=str(database_config["host"]).strip(),
            port=int(database_config.get("port", 1433)),
            database=str(database_config["database"]).strip(),
            username=str(database_config["username"]).strip(),
            password=str(database_config["password"]),
            driver=str(database_config.get("driver", "ODBC Driver 17 for SQL Server")).strip(),
            encrypt=bool(database_config.get("encrypt", False)),
            trust_server_certificate=bool(database_config.get("trust_server_certificate", True)),
            timeout=int(database_config.get("timeout", 30)),
        )


class MssqlClient:
    """MSSQL 조회 실행 클라이언트."""

    def __init__(self, connection_config: MssqlConnectionConfig) -> None:
        """MSSQL 클라이언트를 초기화한다."""
        self.connection_config = connection_config
        self._engine: Engine | None = None

    def execute_query(self, sql: str) -> pd.DataFrame:
        """
        역할:
            입력 SQL을 MSSQL에 조회 실행하고 결과를 DataFrame으로 반환한다.

        Args:
            sql (str):
                역할: SQL Guard를 통과한 조회 SQL 문자열이다.
                값: SELECT 또는 WITH 구문 기반 단일 SQL 텍스트가 들어온다.
                전달 출처: `SqlExecutorService.run_query()`에서 전달된다.
                주의사항: 검증되지 않은 SQL을 직접 전달하면 안전성 보장이 깨질 수 있다.

        Returns:
            pd.DataFrame: 조회 결과를 컬럼/행 구조의 DataFrame으로 반환한다.

        Raises:
            RuntimeError: 엔진 생성/연결/실행 단계에서 SQLAlchemy 예외가 발생하면 래핑해 전파한다.
        """
        logger.info("MSSQL 조회 시작: host=%s, database=%s", self.connection_config.host, self.connection_config.database)
        engine = self._get_engine()
        try:
            with engine.connect() as connection:
                dataframe = pd.read_sql_query(sql=text(sql), con=connection)
        except SQLAlchemyError as error:
            logger.exception("MSSQL 조회 실패")
            raise RuntimeError("MSSQL 조회 실행 중 오류가 발생했습니다.") from error

        logger.info("MSSQL 조회 완료: row_count=%d", len(dataframe))
        return dataframe

    def close(self) -> None:
        """엔진 자원을 해제한다."""
        if self._engine is None:
            return
        self._engine.dispose()
        self._engine = None
        logger.info("MSSQL 엔진 자원 해제 완료")

    def _get_engine(self) -> Engine:
        """MSSQL SQLAlchemy 엔진을 필요 시 생성해 반환한다."""
        if self._engine is not None:
            return self._engine
        connection_url = self._build_connection_url()
        try:
            self._engine = create_engine(connection_url, pool_pre_ping=True, future=True)
        except SQLAlchemyError as error:
            logger.exception("MSSQL 엔진 생성 실패")
            raise RuntimeError("MSSQL 엔진 생성 중 오류가 발생했습니다.") from error
        return self._engine

    def _build_connection_url(self) -> str:
        """config 기반 MSSQL ODBC 연결 URL을 생성한다."""
        conf = self.connection_config
        query_params = {
            "driver": conf.driver,
            "Encrypt": "yes" if conf.encrypt else "no",
            "TrustServerCertificate": "yes" if conf.trust_server_certificate else "no",
            "Connection Timeout": str(conf.timeout),
        }
        query_text = "&".join(f"{key}={quote_plus(value)}" for key, value in query_params.items())
        username = quote_plus(conf.username)
        password = quote_plus(conf.password)
        host = conf.host
        database = quote_plus(conf.database)
        return f"mssql+pyodbc://{username}:{password}@{host}:{conf.port}/{database}?{query_text}"
