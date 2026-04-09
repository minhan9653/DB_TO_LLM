# 이 파일은 SqlGuard의 조회 전용 SQL 검증 규칙을 확인한다.
# 허용 쿼리 통과, 금지 키워드 차단, 다중 문장 차단을 최소 케이스로 검증한다.
# 검증 실패 메시지가 명확히 발생하는지 함께 확인한다.
# 외부 DB 연결 없이 guard 로직만 독립 테스트한다.

from __future__ import annotations

import unittest

from Root_Stream.services.sql.sql_guard import SqlGuard


class SqlGuardTests(unittest.TestCase):
    """SqlGuard 핵심 동작 테스트."""

    def setUp(self) -> None:
        self.guard = SqlGuard(allow_only_select=True)

    def test_validate_query_sql_passes_for_select(self) -> None:
        sql = "SELECT TOP 10 * FROM ERROR_LOG_DATA ORDER BY EVENTTIME DESC"
        validated = self.guard.validate_query_sql(sql)
        self.assertEqual(validated, sql)

    def test_validate_query_sql_rejects_forbidden_keyword(self) -> None:
        with self.assertRaises(ValueError):
            self.guard.validate_query_sql("DELETE FROM ERROR_LOG_DATA")

    def test_validate_query_sql_rejects_multiple_statements(self) -> None:
        with self.assertRaises(ValueError):
            self.guard.validate_query_sql("SELECT 1; SELECT 2;")


if __name__ == "__main__":
    unittest.main()
