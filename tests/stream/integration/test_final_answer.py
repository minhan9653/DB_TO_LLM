# 이 파일은 final_answer_node의 다양한 시나리오를 통합 테스트한다.
# GENERAL, DB_ONLY, RAG_ONLY, DB_THEN_RAG 각 경로에서 올바른 답변이 생성되는지 검증한다.
# 모든 테스트는 Mock LLM을 사용해 외부 의존성 없이 동작한다.

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.final_answer_node import final_answer_node


@pytest.fixture
def minimal_state(sample_config) -> GraphState:
    """최소한의 GraphState 기본값을 반환한다."""
    return {
        "question": "테스트 질문",
        "config_path": None,
        "_config_override": sample_config,
        "errors": [],
        "trace_logs": [],
    }


class TestFinalAnswerNode:
    """final_answer_node()의 다양한 시나리오를 검증한다."""

    # ---------------------------------------------------------------------------
    # GENERAL 경로
    # ---------------------------------------------------------------------------

    def test_general_path_uses_existing_answer(self, minimal_state: GraphState) -> None:
        """GENERAL 경로에서 기존 final_answer를 그대로 사용해야 한다."""
        state = {
            **minimal_state,
            "query_type": "GENERAL",
            "final_answer": "이미 준비된 일반 답변입니다.",
        }
        result = final_answer_node(state)
        assert result["final_answer"] == "이미 준비된 일반 답변입니다."

    def test_general_path_no_extra_llm_call(self, minimal_state: GraphState) -> None:
        """GENERAL 경로에서 기존 답변이 있으면 LLM을 추가 호출하지 않아야 한다."""
        state = {
            **minimal_state,
            "query_type": "GENERAL",
            "final_answer": "기존 답변",
        }
        with patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen:
            final_answer_node(state)
            mock_gen.assert_not_called()

    # ---------------------------------------------------------------------------
    # DB_ONLY 경로
    # ---------------------------------------------------------------------------

    def test_db_only_uses_db_summary(self, minimal_state: GraphState) -> None:
        """DB_ONLY 경로에서 db_summary로 final_answer를 생성해야 한다."""
        state = {
            **minimal_state,
            "query_type": "DB_ONLY",
            "db_summary": "조회 결과: 상위 5개 제품의 매출이 총 1억원입니다.",
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "최종 답변 프롬프트"
            mock_gen.return_value = "상위 5개 제품의 매출 합계는 1억원입니다."
            result = final_answer_node(state)

        assert result["final_answer"] == "상위 5개 제품의 매출 합계는 1억원입니다."
        mock_gen.assert_called_once()

    # ---------------------------------------------------------------------------
    # RAG_ONLY 경로
    # ---------------------------------------------------------------------------

    def test_rag_only_uses_contexts(self, minimal_state: GraphState) -> None:
        """RAG_ONLY 경로에서 retrieved_contexts로 final_answer를 생성해야 한다."""
        state = {
            **minimal_state,
            "query_type": "RAG_ONLY",
            "retrieved_contexts": [
                {"chunk_id": "c1", "text": "오류 E1001은 네트워크 문제입니다.", "source": "doc.md", "score": 0.9}
            ],
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "프롬프트"
            mock_gen.return_value = "E1001 오류는 네트워크 문제로 발생합니다."
            result = final_answer_node(state)

        assert result["final_answer"] == "E1001 오류는 네트워크 문제로 발생합니다."

    # ---------------------------------------------------------------------------
    # DB_THEN_RAG 경로
    # ---------------------------------------------------------------------------

    def test_db_then_rag_combines_sources(self, minimal_state: GraphState) -> None:
        """DB_THEN_RAG 경로에서 db_summary와 contexts를 모두 활용해야 한다."""
        state = {
            **minimal_state,
            "query_type": "DB_THEN_RAG",
            "db_summary": "E1001이 42회 발생.",
            "retrieved_contexts": [
                {"chunk_id": "c1", "text": "E1001은 네트워크 오류입니다.", "source": "doc.md", "score": 0.9}
            ],
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "복합 프롬프트"
            mock_gen.return_value = "E1001 오류가 42회 발생했으며 네트워크 문제입니다."
            result = final_answer_node(state)

        assert result["final_answer"] is not None
        mock_gen.assert_called_once()

    # ---------------------------------------------------------------------------
    # 에러 처리
    # ---------------------------------------------------------------------------

    def test_no_information_returns_error_message(self, minimal_state: GraphState) -> None:
        """답변 재료가 없을 때 오류 메시지를 반환하고 errors에 기록해야 한다."""
        state = {
            **minimal_state,
            "query_type": "DB_ONLY",
            "db_summary": None,
            "retrieved_contexts": [],
            "final_answer": None,
        }
        result = final_answer_node(state)
        # final_answer가 설정되어야 함 (오류 메시지라도)
        assert result.get("final_answer") is not None
        # errors에 무언가 기록되어야 함
        assert len(result.get("errors", [])) > 0

    def test_llm_error_adds_to_errors(self, minimal_state: GraphState) -> None:
        """LLM 호출 실패 시 errors에 오류가 기록되고 fallback 메시지가 반환되어야 한다."""
        state = {
            **minimal_state,
            "query_type": "DB_ONLY",
            "db_summary": "조회 결과 있음.",
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "프롬프트"
            mock_gen.side_effect = RuntimeError("LLM 연결 실패")
            result = final_answer_node(state)

        assert len(result.get("errors", [])) > 0
        assert result.get("final_answer") is not None  # fallback 메시지가 있어야 함

    # ---------------------------------------------------------------------------
    # trace_logs 검증
    # ---------------------------------------------------------------------------

    def test_trace_log_added(self, minimal_state: GraphState) -> None:
        """final_answer_node 실행 후 trace_logs에 항목이 추가되어야 한다."""
        state = {
            **minimal_state,
            "query_type": "GENERAL",
            "final_answer": "이미 있는 답변",
        }
        result = final_answer_node(state)
        assert len(result.get("trace_logs", [])) > 0
