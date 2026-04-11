# 이 파일은 stream/nodes/router.py의 route_by_query_type() 함수를 단위 테스트한다.
# 모든 query_type에 대해 올바른 노드 이름이 반환되는지 검증한다.
# GraphState dict를 직접 생성해 외부 의존성 없이 테스트한다.

from __future__ import annotations

import pytest

from src.db_to_llm.stream.nodes.router import _ROUTE_MAP, route_by_query_type
from src.db_to_llm.stream.planner.models import VALID_QUERY_TYPES


class TestRouteByQueryType:
    """route_by_query_type() 함수의 분기 로직을 검증한다."""

    def _state(self, query_type: str) -> dict:
        """지정된 query_type을 가진 최소 GraphState를 반환한다."""
        return {"query_type": query_type, "question": "테스트 질문"}

    # ---------------------------------------------------------------------------
    # DB 경로 테스트
    # ---------------------------------------------------------------------------

    def test_db_only_routes_to_generate_sql(self) -> None:
        """DB_ONLY는 generate_sql_node로 라우팅되어야 한다."""
        result = route_by_query_type(self._state("DB_ONLY"))
        assert result == "generate_sql_node"

    def test_db_then_rag_routes_to_generate_sql(self) -> None:
        """DB_THEN_RAG는 먼저 generate_sql_node로 라우팅되어야 한다."""
        result = route_by_query_type(self._state("DB_THEN_RAG"))
        assert result == "generate_sql_node"

    def test_db_then_general_routes_to_generate_sql(self) -> None:
        """DB_THEN_GENERAL도 먼저 generate_sql_node로 라우팅되어야 한다."""
        result = route_by_query_type(self._state("DB_THEN_GENERAL"))
        assert result == "generate_sql_node"

    # ---------------------------------------------------------------------------
    # RAG 경로 테스트
    # ---------------------------------------------------------------------------

    def test_rag_only_routes_to_retrieve_rag(self) -> None:
        """RAG_ONLY는 retrieve_rag_node로 라우팅되어야 한다."""
        result = route_by_query_type(self._state("RAG_ONLY"))
        assert result == "retrieve_rag_node"

    def test_rag_then_general_routes_to_retrieve_rag(self) -> None:
        """RAG_THEN_GENERAL도 먼저 retrieve_rag_node로 라우팅되어야 한다."""
        result = route_by_query_type(self._state("RAG_THEN_GENERAL"))
        assert result == "retrieve_rag_node"

    # ---------------------------------------------------------------------------
    # GENERAL 경로 테스트
    # ---------------------------------------------------------------------------

    def test_general_routes_to_general_answer(self) -> None:
        """GENERAL은 general_answer_node로 라우팅되어야 한다."""
        result = route_by_query_type(self._state("GENERAL"))
        assert result == "general_answer_node"

    # ---------------------------------------------------------------------------
    # 대소문자 비구분 테스트
    # ---------------------------------------------------------------------------

    def test_lowercase_query_type_handled(self) -> None:
        """소문자 query_type도 대소문자 변환 후 올바르게 처리되어야 한다."""
        result = route_by_query_type(self._state("db_only"))
        assert result == "generate_sql_node"

    def test_mixed_case_query_type_handled(self) -> None:
        """혼합 케이스도 올바르게 처리되어야 한다."""
        result = route_by_query_type(self._state("Rag_Only"))
        assert result == "retrieve_rag_node"

    # ---------------------------------------------------------------------------
    # 폴백 테스트
    # ---------------------------------------------------------------------------

    def test_unknown_query_type_fallback_to_general(self) -> None:
        """알 수 없는 query_type은 general_answer_node로 폴백되어야 한다."""
        result = route_by_query_type(self._state("UNKNOWN_TYPE"))
        assert result == "general_answer_node"

    def test_missing_query_type_fallback_to_general(self) -> None:
        """query_type이 없으면 GENERAL로 폴백되어야 한다."""
        result = route_by_query_type({"question": "질문"})
        assert result == "general_answer_node"

    # ---------------------------------------------------------------------------
    # _ROUTE_MAP 커버리지 테스트
    # ---------------------------------------------------------------------------

    def test_route_map_covers_all_valid_types(self) -> None:
        """_ROUTE_MAP이 모든 VALID_QUERY_TYPES를 포함해야 한다."""
        for query_type in VALID_QUERY_TYPES:
            assert query_type in _ROUTE_MAP, f"{query_type}가 _ROUTE_MAP에 없습니다"

    def test_all_valid_types_route_to_known_nodes(self) -> None:
        """모든 VALID_QUERY_TYPES가 알려진 노드 이름 중 하나로 라우팅되어야 한다."""
        expected_nodes = {"generate_sql_node", "retrieve_rag_node", "general_answer_node"}
        for query_type in VALID_QUERY_TYPES:
            result = route_by_query_type(self._state(query_type))
            assert result in expected_nodes, (
                f"{query_type}가 예상치 못한 노드로 라우팅됩니다: {result}"
            )
