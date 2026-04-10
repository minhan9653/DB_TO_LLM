# 이 파일은 테스트 전역에서 공통으로 사용하는 fixture 로더를 제공한다.
# JSON/SQL 샘플을 한 곳에서 읽어 중복 코드를 줄이고 테스트 가독성을 높인다.
# 외부 시스템 없이 재현 가능한 데이터를 tests/fixtures에서 일관되게 공급한다.
# unit/integration/e2e 테스트가 같은 입력 데이터를 공유하도록 경로를 표준화한다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixture_root() -> Path:
    """
    테스트 fixture 루트 경로를 반환한다.

    Returns:
        Path: tests/fixtures 절대 경로.
    """
    return FIXTURE_ROOT


@pytest.fixture
def sample_sql(fixture_root: Path) -> str:
    """
    샘플 SQL 문자열 fixture를 반환한다.

    Args:
        fixture_root: fixture 루트 경로.

    Returns:
        str: 샘플 SQL.
    """
    return (fixture_root / "sql" / "sample_generated_sql.sql").read_text(encoding="utf-8")


@pytest.fixture
def sample_db_rows(fixture_root: Path) -> list[dict[str, Any]]:
    """
    샘플 DB row fixture를 반환한다.

    Args:
        fixture_root: fixture 루트 경로.

    Returns:
        list[dict[str, Any]]: 샘플 DB rows.
    """
    return json.loads((fixture_root / "db" / "sample_db_rows.json").read_text(encoding="utf-8"))


@pytest.fixture
def sample_rag_contexts(fixture_root: Path) -> list[dict[str, Any]]:
    """
    샘플 RAG 컨텍스트 fixture를 반환한다.

    Args:
        fixture_root: fixture 루트 경로.

    Returns:
        list[dict[str, Any]]: 샘플 RAG 컨텍스트.
    """
    return json.loads((fixture_root / "rag" / "sample_retrieved_context.json").read_text(encoding="utf-8"))

