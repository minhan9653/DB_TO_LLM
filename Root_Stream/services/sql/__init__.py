# 이 파일은 SQL 실행 관련 서비스 패키지의 공통 진입점을 제공한다.
# 의존성(sqlalchemy, pandas, pyodbc)이 없는 환경에서도 패키지 import 실패를 막는다.
# 실제 DB 실행 관련 클래스는 접근 시점에 지연 import하여 하위 호환성을 유지한다.
# 기존 STREAM SQL 생성 단계는 이 패키지와 독립적으로 동작하도록 분리한다.

from Root_Stream.services.sql.sql_guard import SqlGuard

__all__ = [
    "MssqlClient",
    "MssqlConnectionConfig",
    "SqlExecutorService",
    "SqlGuard",
    "create_sql_executor_from_config_path",
]


def __getattr__(name: str):
    """DB 실행 관련 심볼을 필요 시점에 로딩한다."""
    if name in {"MssqlClient", "MssqlConnectionConfig"}:
        from Root_Stream.services.sql.mssql_client import MssqlClient, MssqlConnectionConfig

        return {"MssqlClient": MssqlClient, "MssqlConnectionConfig": MssqlConnectionConfig}[name]

    if name in {"SqlExecutorService", "create_sql_executor_from_config_path"}:
        from Root_Stream.services.sql.sql_executor_service import SqlExecutorService, create_sql_executor_from_config_path

        return {
            "SqlExecutorService": SqlExecutorService,
            "create_sql_executor_from_config_path": create_sql_executor_from_config_path,
        }[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
