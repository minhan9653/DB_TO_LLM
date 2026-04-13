# 이 파일은 src/db_to_llm 패키지 테스트를 위한 pytest 공통 픽스처를 정의한다.
# mock LLM 클라이언트, 샘플 config, PlannerPlan 픽스처를 제공한다.
# tests/ 하위 모든 테스트 파일에서 자동으로 사용된다.

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.db_to_llm.stream.planner.models import PlannerPlan, PlannerStep


# ---------------------------------------------------------------------------
# 샘플 설정 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_config() -> dict[str, Any]:
    """테스트에서 사용할 최소 config dict를 반환한다."""
    return {
        "llm_provider": "ollama",
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "qwen2.5:14b",
            "request_timeout": 60,
        },
        "openai": {
            "model": "gpt-4o",
            "api_key": "test-key",
        },
        "database": {
            "driver": "ODBC Driver 17 for SQL Server",
            "server": "localhost",
            "database": "TestDB",
            "username": "sa",
            "password": "test-password",
        },
        "sql": {
            "max_rows": 1000,
            "timeout_seconds": 30,
        },
        "retrieval": {
            "chroma_path": "/tmp/test_chroma",
            "collection_name": "test_collection",
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "top_k": 5,
        },
        "stream": {
            "prompts": {
                "prompt_file": None,
            }
        },
    }


# ---------------------------------------------------------------------------
# Mock LLM 클라이언트 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_client() -> MagicMock:
    """generate() 메서드를 가진 Mock LLM 클라이언트를 반환한다."""
    client = MagicMock()
    client.provider_name = "mock"
    client.generate.return_value = "Mock LLM 응답"
    return client


# ---------------------------------------------------------------------------
# 샘플 PlannerPlan 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def plan_db_only() -> PlannerPlan:
    """DB_ONLY plan 픽스처를 반환한다."""
    return PlannerPlan(
        is_composite=False,
        query_type="DB_ONLY",
        steps=[PlannerStep(step=1, type="db", goal="DB에서 데이터 조회", depends_on=[])],
    )


@pytest.fixture
def plan_rag_only() -> PlannerPlan:
    """RAG_ONLY plan 픽스처를 반환한다."""
    return PlannerPlan(
        is_composite=False,
        query_type="RAG_ONLY",
        steps=[PlannerStep(step=1, type="rag", goal="문서에서 답변 검색", depends_on=[])],
    )


@pytest.fixture
def plan_general() -> PlannerPlan:
    """GENERAL plan 픽스처를 반환한다."""
    return PlannerPlan(
        is_composite=False,
        query_type="GENERAL",
        steps=[PlannerStep(step=1, type="general", goal="일반 지식으로 답변", depends_on=[])],
    )


@pytest.fixture
def plan_db_then_rag() -> PlannerPlan:
    """DB_THEN_RAG 복합 plan 픽스처를 반환한다."""
    return PlannerPlan(
        is_composite=True,
        query_type="DB_THEN_RAG",
        steps=[
            PlannerStep(step=1, type="db", goal="DB에서 오류 코드 조회", depends_on=[]),
            PlannerStep(step=2, type="rag", goal="오류 코드 관련 문서 검색", depends_on=[1]),
        ],
    )
