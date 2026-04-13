# 이 파일은 RAG_ONLY 흐름의 통합 테스트를 정의한다.
# retrieve_rag_node → final_answer_node 경로를 Mock으로 검증한다.
# 실제 ChromaDB/LLM 연결 없이 동작한다.

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.final_answer_node import final_answer_node
from src.db_to_llm.stream.nodes.retrieve_rag_node import retrieve_rag_node


@pytest.fixture
def rag_base_state(sample_config) -> GraphState:
    """RAG_ONLY 시나리오의 기본 GraphState를 반환한다."""
    return {
        "question": "오류 코드 E1003의 원인이 뭔가요?",
        "query_type": "RAG_ONLY",
        "planner_result": {
            "is_composite": False,
            "query_type": "RAG_ONLY",
            "steps": [{"step": 1, "type": "rag", "goal": "오류 원인 문서 검색", "depends_on": []}],
        },
        "planner_steps": [
            {"step": 1, "type": "rag", "goal": "오류 원인 문서 검색", "depends_on": []}
        ],
        "config_path": None,
        "_config_override": sample_config,
        "errors": [],
        "trace_logs": [],
    }


class TestRagOnlyFlow:
    """RAG_ONLY 통합 흐름을 검증한다."""

    def test_retrieve_rag_returns_contexts(self, rag_base_state: GraphState) -> None:
        """retrieve_rag_node가 retrieved_contexts를 state에 저장해야 한다."""
        mock_contexts = [
            {"chunk_id": "c1", "text": "E1003는 타임아웃 오류입니다.", "source": "manual.md", "score": 0.95},
            {"chunk_id": "c2", "text": "타임아웃 설정은 config에서 변경 가능합니다.", "source": "config.md", "score": 0.88},
        ]
        with patch("src.db_to_llm.stream.nodes.retrieve_rag_node.retrieve_contexts") as mock_ret:
            mock_ret.return_value = mock_contexts
            result = retrieve_rag_node(rag_base_state)

        assert "retrieved_contexts" in result
        assert len(result["retrieved_contexts"]) == 2

    def test_retrieve_rag_called_with_question(self, rag_base_state: GraphState) -> None:
        """retrieve_rag_node는 question을 검색 쿼리로 사용해야 한다."""
        with patch("src.db_to_llm.stream.nodes.retrieve_rag_node.retrieve_contexts") as mock_ret:
            mock_ret.return_value = []
            retrieve_rag_node(rag_base_state)

        call_args = mock_ret.call_args
        query_arg = call_args[0][0]
        assert "오류 코드" in query_arg or "E1003" in query_arg

    def test_retrieve_rag_no_db_summary(self, rag_base_state: GraphState) -> None:
        """RAG_ONLY는 db_summary가 없으므로 질문만 사용해야 한다."""
        state_no_db = {**rag_base_state, "db_summary": None}
        with patch("src.db_to_llm.stream.nodes.retrieve_rag_node.retrieve_contexts") as mock_ret:
            mock_ret.return_value = []
            retrieve_rag_node(state_no_db)

        call_args = mock_ret.call_args
        query_arg = call_args[0][0]
        # DB 요약 없이 질문만 포함되어야 함
        assert "DB 조회 결과 요약" not in query_arg

    def test_empty_contexts_handled_gracefully(self, rag_base_state: GraphState) -> None:
        """검색 결과가 없을 때도 오류 없이 처리되어야 한다."""
        with patch("src.db_to_llm.stream.nodes.retrieve_rag_node.retrieve_contexts") as mock_ret:
            mock_ret.return_value = []
            result = retrieve_rag_node(rag_base_state)

        assert result.get("retrieved_contexts") == []

    def test_final_answer_uses_contexts(self, rag_base_state: GraphState) -> None:
        """final_answer_node가 retrieved_contexts로 답변을 생성해야 한다."""
        state_with_contexts = {
            **rag_base_state,
            "retrieved_contexts": [
                {"chunk_id": "c1", "text": "E1003는 타임아웃 오류입니다.", "source": "manual.md", "score": 0.95}
            ],
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "RAG 답변 프롬프트"
            mock_gen.return_value = "E1003는 타임아웃 오류이며, config에서 timeout 값을 조정할 수 있습니다."
            result = final_answer_node(state_with_contexts)

        assert result.get("final_answer") is not None
        assert "오류" in result["final_answer"] or "timeout" in result["final_answer"].lower()

    def test_final_answer_no_contexts_generates_fallback(self, rag_base_state: GraphState) -> None:
        """검색 결과가 없을 때 final_answer_node가 LLM 폴백 또는 안내 메시지를 반환해야 한다."""
        state_empty = {
            **rag_base_state,
            "retrieved_contexts": [],
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "프롬프트"
            mock_gen.return_value = "관련 문서를 찾을 수 없습니다."
            result = final_answer_node(state_empty)

        # 오류 없이 final_answer가 설정되어야 함
        assert "final_answer" in result
