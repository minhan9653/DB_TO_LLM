# 이 파일은 생성된 SQL이 조회용인지 검증하는 안전 가드를 담당한다.
# SQL 실행 전에 위험 구문을 차단해 데이터 변경/DDL 실행을 방지한다.
# sql_executor_service가 이 모듈을 호출해 검증 후 DB 실행으로 넘긴다.
# Notebook/CLI에서 동일한 검증 로직을 재사용하도록 공통 서비스로 구성한다.

from __future__ import annotations

import re

from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)

FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "DENY",
)

FORBIDDEN_PATTERN = re.compile(r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE)
SELECT_INTO_PATTERN = re.compile(r"\bSELECT\b[\s\S]*\bINTO\b", re.IGNORECASE)


class SqlGuard:
    """조회용 SQL만 허용하는 검증 클래스."""

    def __init__(self, allow_only_select: bool = True) -> None:
        """SQL 검증 옵션을 초기화한다."""
        self.allow_only_select = allow_only_select

    def validate_query_sql(self, sql: str) -> str:
        """
        역할:
            입력된 SQL 문자열을 검증해 조회용 단일 SQL만 통과시킨다.

        Args:
            sql (str):
                역할: 상위 SQL 생성 단계에서 만들어진 SQL 문자열이다.
                값: 공백/개행/주석이 포함될 수 있는 SQL 텍스트가 들어온다.
                전달 출처: STREAM 결과(query) 또는 Notebook 테스트 코드에서 전달된다.
                주의사항: 빈 문자열, 다중 문장, 금지 키워드가 포함되면 예외를 발생시킨다.

        Returns:
            str: 검증을 통과한 단일 조회 SQL 문자열을 반환한다.

        Raises:
            ValueError: 빈 SQL, 다중 SQL, 금지 키워드, 비조회 시작 구문일 때 발생한다.
        """
        logger.info("SQL 검증 시작")
        normalized_sql = self._normalize_sql_text(sql)
        if not normalized_sql:
            raise ValueError("SQL 검증 실패: 비어 있는 SQL은 실행할 수 없습니다.")

        statements = self._split_sql_statements(normalized_sql)
        if len(statements) != 1:
            raise ValueError("SQL 검증 실패: 다중 SQL 문장은 허용되지 않습니다.")

        statement = statements[0].strip()
        if self.allow_only_select:
            self._validate_query_start(statement)
        self._validate_forbidden_keywords(statement)
        self._validate_select_into(statement)
        logger.info("SQL 검증 완료")
        return statement

    def _normalize_sql_text(self, sql: str) -> str:
        """검증 전에 Markdown 코드블록 래퍼를 제거하고 공백을 정리한다."""
        stripped_sql = sql.strip()
        if not stripped_sql:
            return ""

        if not stripped_sql.startswith("```"):
            return stripped_sql

        lines = stripped_sql.splitlines()
        if len(lines) < 2:
            return stripped_sql

        first_line = lines[0].strip()
        last_line = lines[-1].strip()
        if not first_line.startswith("```") or last_line != "```":
            return stripped_sql

        unwrapped_sql = "\n".join(lines[1:-1]).strip()
        if not unwrapped_sql:
            raise ValueError("SQL 검증 실패: 코드블록 내부 SQL이 비어 있습니다.")

        logger.info("SQL 코드블록 래퍼를 제거하고 검증을 진행합니다.")
        return unwrapped_sql

    def _validate_query_start(self, statement: str) -> None:
        """조회용 SQL 시작 구문(SELECT/WITH)인지 확인한다."""
        query_body = self._remove_leading_comments(statement).lstrip()
        upper_query_body = query_body.upper()
        if upper_query_body.startswith("SELECT") or upper_query_body.startswith("WITH"):
            return
        raise ValueError("SQL 검증 실패: SELECT 또는 WITH로 시작하는 조회 SQL만 허용됩니다.")

    def _validate_forbidden_keywords(self, statement: str) -> None:
        """쓰기/DDL 계열 금지 키워드 포함 여부를 확인한다."""
        matched = FORBIDDEN_PATTERN.search(statement)
        if not matched:
            return
        blocked_keyword = matched.group(1).upper()
        raise ValueError(f"SQL 검증 실패: 금지 키워드가 포함되어 있습니다. keyword={blocked_keyword}")

    def _validate_select_into(self, statement: str) -> None:
        """SELECT INTO 패턴을 차단한다."""
        if SELECT_INTO_PATTERN.search(statement):
            raise ValueError("SQL 검증 실패: SELECT INTO 구문은 데이터 생성 위험으로 차단됩니다.")

    def _split_sql_statements(self, sql: str) -> list[str]:
        """세미콜론을 기준으로 SQL 문장을 분리하되 문자열 리터럴은 보존한다."""
        statements: list[str] = []
        current_chars: list[str] = []
        in_single_quote = False
        in_double_quote = False
        index = 0

        while index < len(sql):
            char = sql[index]
            if char == "'" and not in_double_quote:
                if in_single_quote and index + 1 < len(sql) and sql[index + 1] == "'":
                    current_chars.append(char)
                    current_chars.append(sql[index + 1])
                    index += 2
                    continue
                in_single_quote = not in_single_quote
                current_chars.append(char)
                index += 1
                continue

            if char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current_chars.append(char)
                index += 1
                continue

            if char == ";" and not in_single_quote and not in_double_quote:
                statement = "".join(current_chars).strip()
                if statement:
                    statements.append(statement)
                current_chars = []
                index += 1
                continue

            current_chars.append(char)
            index += 1

        if in_single_quote or in_double_quote:
            raise ValueError("SQL 검증 실패: 문자열 리터럴 따옴표가 닫히지 않았습니다.")

        tail_statement = "".join(current_chars).strip()
        if tail_statement:
            statements.append(tail_statement)
        return statements

    def _remove_leading_comments(self, sql: str) -> str:
        """SQL 선행 주석을 제거해 첫 구문 키워드를 안정적으로 확인한다."""
        remaining_sql = sql.lstrip()
        while True:
            if remaining_sql.startswith("--"):
                line_end = remaining_sql.find("\n")
                if line_end == -1:
                    return ""
                remaining_sql = remaining_sql[line_end + 1 :].lstrip()
                continue

            if remaining_sql.startswith("/*"):
                block_end = remaining_sql.find("*/")
                if block_end == -1:
                    raise ValueError("SQL 검증 실패: 블록 주석이 닫히지 않았습니다.")
                remaining_sql = remaining_sql[block_end + 2 :].lstrip()
                continue
            return remaining_sql
