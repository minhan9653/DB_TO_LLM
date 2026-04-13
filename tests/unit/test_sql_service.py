# 이 파일은 SQL 서비스의 검증 함수(validate_sql) 동작을 단위 테스트한다.
# SELECT 허용/금지 키워드 차단/빈 SQL 처리 규칙을 외부 의존 없이 확인한다.
# SQL Guard 우회가 발생하지 않도록 핵심 경로를 고정 테스트로 유지한다.

from __future__ import annotations

import pytest

from src.db_to_llm.stream.services.sql_service import validate_sql


def test_validate_sql_success(sample_sql: str) -> None:
    """
    정상 SELECT SQL이 그대로 반환되는지 확인한다.

    Args:
        sample_sql: 샘플 SQL fixture.
    """
    result = validate_sql(sample_sql)
    assert isinstance(result, str)
    assert "SELECT" in result.upper()


def test_validate_sql_rejects_delete() -> None:
    """DELETE 문이 ValueError를 발생시키는지 확인한다."""
    with pytest.raises(ValueError, match="DELETE"):
        validate_sql("DELETE FROM ERROR_LOG_DATA")


def test_validate_sql_rejects_empty_sql() -> None:
    """빈 SQL 문자열이 ValueError를 발생시키는지 확인한다."""
    with pytest.raises(ValueError):
        validate_sql("   ")
