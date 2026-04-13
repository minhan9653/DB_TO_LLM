# 이 파일은 SQL 검증과 DB 실행을 담당하는 서비스 함수들을 담는다.
# validate_sql()은 SELECT-only 검증을 수행하고 안전한 SQL만 통과시킨다.
# execute_sql()은 검증 완료된 SQL을 DB에서 실행하고 결과를 반환한다.
# 두 함수 모두 validate_sql_node, execute_sql_node에서 호출한다.

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# SQL을 변경하는 금지 키워드 목록 (Rule.md 7-1 규정)
FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "MERGE", "CREATE",
    "GRANT", "REVOKE", "DENY",
)

FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)
SELECT_INTO_PATTERN = re.compile(r"\bSELECT\b[\s\S]*?\bINTO\b", re.IGNORECASE)
CODE_BLOCK_PATTERN = re.compile(r"```(?:[^\n`]*)?\n?([\s\S]*?)\n?```", re.IGNORECASE)


def validate_sql(sql: str) -> str:
    """
    입력된 SQL을 검증해 안전한 SELECT 쿼리만 통과시킨다.
    마크다운 코드블록이 있으면 제거하고 검증한다.

    Args:
        sql: 검증할 SQL 문자열.

    Returns:
        str: 검증 통과한 단일 SELECT SQL.

    Raises:
        ValueError: 빈 SQL, 금지 키워드, 다중 구문, SELECT 외 시작, SELECT INTO 감지 시 발생.
    """
    logger.info("SQL 검증 시작")

    # 코드블록 제거
    cleaned_sql = _remove_code_block(sql).strip()

    if not cleaned_sql:
        raise ValueError("SQL 검증 실패: 비어 있는 SQL은 실행할 수 없습니다.")

    # 다중 SQL 문장 차단 (문자열 내부 세미콜론은 허용)
    statements = _split_sql_statements(cleaned_sql)
    if len(statements) != 1:
        raise ValueError(
            f"SQL 검증 실패: 다중 SQL 문장은 허용되지 않습니다. ({len(statements)}개 감지)"
        )

    statement = statements[0].strip()

    # SELECT로 시작하는지 확인
    if not re.match(r"^\s*SELECT\b", statement, re.IGNORECASE):
        raise ValueError("SQL 검증 실패: SELECT 쿼리만 허용됩니다.")

    # 금지 키워드 확인
    match = FORBIDDEN_PATTERN.search(statement)
    if match:
        raise ValueError(f"SQL 검증 실패: 금지된 키워드 감지: '{match.group(0)}'")

    # SELECT INTO 차단
    if SELECT_INTO_PATTERN.search(statement):
        raise ValueError("SQL 검증 실패: SELECT INTO는 허용되지 않습니다.")

    logger.info("SQL 검증 완료")
    return statement


def execute_sql(
    validated_sql: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    검증 완료된 SQL을 DB에서 실행하고 결과를 반환한다.

    Args:
        validated_sql: validate_sql()을 통과한 SQL 문자열.
        config: load_config()로 읽은 전체 설정 dict.

    Returns:
        dict: columns, rows, row_count 키를 포함하는 실행 결과.

    Raises:
        RuntimeError: DB 연결 실패 또는 쿼리 실행 오류 시 발생한다.
    """
    logger.info("SQL 실행 시작: sql_length=%d", len(validated_sql))

    db_config = config.get("database", {})
    max_rows = config.get("sql", {}).get("max_rows", 1000)

    try:
        import pyodbc
    except ImportError as error:
        raise ImportError(
            "pyodbc 패키지가 없습니다. `pip install pyodbc`로 설치하세요."
        ) from error

    connection_string = _build_connection_string(db_config)

    try:
        conn = pyodbc.connect(connection_string, timeout=db_config.get("timeout", 30))
        cursor = conn.cursor()
        cursor.execute(validated_sql)
        columns = [col[0] for col in cursor.description]
        raw_rows = cursor.fetchmany(max_rows)
        conn.close()
    except Exception:
        logger.exception("SQL 실행 실패")
        raise RuntimeError("DB 쿼리 실행 중 오류가 발생했습니다.")

    rows = [dict(zip(columns, _serialize_row(row))) for row in raw_rows]
    logger.info("SQL 실행 완료: row_count=%d", len(rows))

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def _build_connection_string(db_config: dict[str, Any]) -> str:
    """config.database 섹션으로 ODBC 연결 문자열을 구성한다."""
    driver = db_config.get("driver", "ODBC Driver 17 for SQL Server")
    host = db_config.get("host", "127.0.0.1")
    port = db_config.get("port", 1433)
    database = db_config.get("database", "")
    username = db_config.get("username", "")
    password = db_config.get("password", "")
    encrypt = "yes" if db_config.get("encrypt", False) else "no"
    trust_cert = "yes" if db_config.get("trust_server_certificate", True) else "no"

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_cert};"
    )


def _remove_code_block(sql: str) -> str:
    """Markdown 코드블록(``` ... ```)을 벗겨내고 내부 텍스트를 반환한다."""
    match = CODE_BLOCK_PATTERN.search(sql.strip())
    if match:
        return match.group(1).strip()
    return sql


def _serialize_row(row: tuple) -> tuple:
    """DB 행의 각 값을 JSON 직렬화 가능한 타입으로 변환한다."""
    result = []
    for val in row:
        if isinstance(val, (datetime, date)):
            result.append(val.isoformat())
        elif isinstance(val, Decimal):
            result.append(float(val))
        elif isinstance(val, bytes):
            result.append(val.hex())
        elif val is None:
            result.append(None)
        else:
            result.append(val)
    return tuple(result)


def _split_sql_statements(sql: str) -> list[str]:
    """
    문자열 리터럴 외부의 세미콜론으로 SQL을 분리한다.
    문자열 내부 세미콜론은 분리하지 않는다.
    """
    statements = []
    current = []
    inside_string = False
    string_char = ""

    for char in sql:
        if not inside_string:
            if char in ("'", '"'):
                inside_string = True
                string_char = char
                current.append(char)
            elif char == ";":
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(char)
        else:
            current.append(char)
            if char == string_char:
                inside_string = False

    remaining = "".join(current).strip()
    if remaining:
        statements.append(remaining)

    return statements
