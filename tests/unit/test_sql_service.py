# 이 파일은 SQL 서비스의 검증 함수(validate_sql) 동작을 단위 테스트한다.
# SELECT 허용/금지 키워드 차단/빈 SQL 처리 규칙을 외부 의존 없이 확인한다.
# SQL Guard 우회가 발생하지 않도록 핵심 경로를 고정 테스트로 유지한다.
# 추후 SQL 정책 변경 시 영향 범위를 빠르게 파악할 수 있도록 단순 사례를 포함한다.

from __future__ import annotations

from db_to_llm.stream.services.sql_service import validate_sql


def test_validate_sql_success(sample_sql: str) -> None:
    """
    정상 SELECT SQL이 유효 판정을 받는지 확인한다.

    Args:
        sample_sql: 샘플 SQL fixture.
    """
    result = validate_sql(sql=sample_sql)
    assert result["is_valid"] is True
    assert "SELECT" in str(result["validated_sql"]).upper()


def test_validate_sql_rejects_delete() -> None:
    """
    DELETE 문이 차단되는지 확인한다.
    """
    result = validate_sql(sql="DELETE FROM ERROR_LOG_DATA")
    assert result["is_valid"] is False
    assert result["error"]


def test_validate_sql_rejects_empty_sql() -> None:
    """
    빈 SQL 문자열이 유효하지 않은지 확인한다.
    """
    result = validate_sql(sql="   ")
    assert result["is_valid"] is False

