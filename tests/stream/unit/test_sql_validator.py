# 이 파일은 sql_service.py의 validate_sql() 함수를 단위 테스트한다.
# SELECT-only 검증, 금지 키워드 차단, 마크다운 코드블록 제거를 검증한다.
# DB 연결 없이 SQL 문자열 검증만 테스트하므로 외부 의존성이 없다.

from __future__ import annotations

import pytest

from src.db_to_llm.stream.services.sql_service import validate_sql


class TestValidateSql:
    """validate_sql() 함수의 동작을 검증한다."""

    # ---------------------------------------------------------------------------
    # 통과해야 하는 케이스
    # ---------------------------------------------------------------------------

    def test_simple_select_passes(self) -> None:
        """단순 SELECT 쿼리는 그대로 통과해야 한다."""
        sql = "SELECT id, name FROM users WHERE active = 1"
        result = validate_sql(sql)
        assert "SELECT" in result.upper()
        assert "users" in result

    def test_select_with_join_passes(self) -> None:
        """JOIN이 포함된 SELECT 쿼리도 통과해야 한다."""
        sql = "SELECT a.id, b.name FROM orders a INNER JOIN customers b ON a.customer_id = b.id"
        result = validate_sql(sql)
        assert result is not None

    def test_select_with_subquery_passes(self) -> None:
        """서브쿼리가 포함된 SELECT는 통과해야 한다."""
        sql = "SELECT * FROM (SELECT id, COUNT(*) as cnt FROM logs GROUP BY id) sub WHERE cnt > 10"
        result = validate_sql(sql)
        assert result is not None

    def test_markdown_code_block_stripped(self) -> None:
        """마크다운 코드블록(```sql ... ```)이 제거되어야 한다."""
        sql = "```sql\nSELECT * FROM products\n```"
        result = validate_sql(sql)
        assert "```" not in result
        assert "SELECT" in result.upper()

    def test_code_block_without_language_stripped(self) -> None:
        """언어 표시 없는 코드블록(``` ... ```)도 제거되어야 한다."""
        sql = "```\nSELECT id FROM items\n```"
        result = validate_sql(sql)
        assert "```" not in result

    def test_whitespace_trimmed(self) -> None:
        """앞뒤 공백이 제거되어야 한다."""
        sql = "   SELECT 1   "
        result = validate_sql(sql)
        assert result == result.strip()

    # ---------------------------------------------------------------------------
    # 차단되어야 하는 케이스
    # ---------------------------------------------------------------------------

    def test_insert_blocked(self) -> None:
        """INSERT 문은 ValueError를 발생시켜야 한다."""
        sql = "INSERT INTO users (name) VALUES ('test')"
        with pytest.raises(ValueError, match="INSERT"):
            validate_sql(sql)

    def test_update_blocked(self) -> None:
        """UPDATE 문은 ValueError를 발생시켜야 한다."""
        sql = "UPDATE users SET name = 'x' WHERE id = 1"
        with pytest.raises(ValueError, match="UPDATE"):
            validate_sql(sql)

    def test_delete_blocked(self) -> None:
        """DELETE 문은 ValueError를 발생시켜야 한다."""
        sql = "DELETE FROM users WHERE id = 1"
        with pytest.raises(ValueError, match="DELETE"):
            validate_sql(sql)

    def test_drop_blocked(self) -> None:
        """DROP TABLE은 ValueError를 발생시켜야 한다."""
        sql = "DROP TABLE users"
        with pytest.raises(ValueError, match="DROP"):
            validate_sql(sql)

    def test_alter_blocked(self) -> None:
        """ALTER TABLE은 ValueError를 발생시켜야 한다."""
        sql = "ALTER TABLE users ADD COLUMN email VARCHAR(100)"
        with pytest.raises(ValueError, match="ALTER"):
            validate_sql(sql)

    def test_truncate_blocked(self) -> None:
        """TRUNCATE는 ValueError를 발생시켜야 한다."""
        sql = "TRUNCATE TABLE logs"
        with pytest.raises(ValueError, match="TRUNCATE"):
            validate_sql(sql)

    def test_exec_blocked(self) -> None:
        """EXEC/EXECUTE는 ValueError를 발생시켜야 한다."""
        sql = "EXEC sp_get_data"
        with pytest.raises(ValueError, match="EXEC"):
            validate_sql(sql)

    def test_select_into_blocked(self) -> None:
        """SELECT INTO는 데이터 변경이므로 차단되어야 한다."""
        sql = "SELECT * INTO backup_table FROM users"
        with pytest.raises(ValueError):
            validate_sql(sql)

    def test_empty_string_blocked(self) -> None:
        """빈 문자열은 ValueError를 발생시켜야 한다."""
        with pytest.raises(ValueError):
            validate_sql("")

    def test_non_select_start_blocked(self) -> None:
        """SELECT로 시작하지 않는 쿼리는 차단되어야 한다."""
        sql = "SHOW TABLES"
        with pytest.raises(ValueError):
            validate_sql(sql)

    def test_case_insensitive_blocking(self) -> None:
        """소문자 금지 키워드도 차단해야 한다."""
        with pytest.raises(ValueError):
            validate_sql("insert into users values (1, 'x')")
        with pytest.raises(ValueError):
            validate_sql("drop table logs")
