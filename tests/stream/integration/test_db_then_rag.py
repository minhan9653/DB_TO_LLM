# 이 파일은 DB_THEN_RAG 복합 흐름의 통합 테스트를 정의한다.
# DB 실행 → RAG 검색 → 최종 답변 생성 경로를 Mock으로 검증한다.
# 실제 DB/ChromaDB/LLM 연결 없이 동작한다.

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.execute_sql_node import execute_sql_node
from src.db_to_llm.stream.nodes.final_answer_node import final_answer_node
from src.db_to_llm.stream.nodes.generate_sql_node import generate_sql_node
from src.db_to_llm.stream.nodes.retrieve_rag_node import retrieve_rag_node
from src.db_to_llm.stream.nodes.summarize_db_node import summarize_db_node
from src.db_to_llm.stream.nodes.validate_sql_node import validate_sql_node


@pytest.fixture
def base_state(sample_config) -> GraphState:
    """DB_THEN_RAG 시나리오의 기본 GraphState를 반환한다."""
    return {
        "question": "지난달 가장 많이 발생한 오류 코드를 조회하고 원인을 알려줘",
        "query_type": "DB_THEN_RAG",
        "planner_result": {
            "is_composite": True,
            "query_type": "DB_THEN_RAG",
            "steps": [
                {"step": 1, "type": "db", "goal": "오류 코드 조회", "depends_on": []},
                {"step": 2, "type": "rag", "goal": "오류 원인 문서 검색", "depends_on": [1]},
            ],
        },
        "planner_steps": [
            {"step": 1, "type": "db", "goal": "오류 코드 조회", "depends_on": []},
            {"step": 2, "type": "rag", "goal": "오류 원인 문서 검색", "depends_on": [1]},
        ],
        "config_path": None,
        "_config_override": sample_config,
        "errors": [],
        "trace_logs": [],
    }


class TestDbThenRagFlow:
    """DB_THEN_RAG 통합 흐름을 노드별로 검증한다."""

    def test_generate_sql_produces_sql(self, base_state: GraphState) -> None:
        """generate_sql_node가 generated_sql을 state에 저장해야 한다."""
        with (
            patch("src.db_to_llm.stream.nodes.generate_sql_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.generate_sql_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "SQL 생성 프롬프트"
            mock_gen.return_value = "SELECT error_code, COUNT(*) FROM logs GROUP BY error_code ORDER BY 2 DESC"

            result = generate_sql_node(base_state)

        assert "generated_sql" in result
        assert result["generated_sql"] is not None

    def test_validate_sql_marks_valid(self, base_state: GraphState) -> None:
        """validate_sql_node가 유효한 SQL에서 sql_validation_passed=True를 설정해야 한다."""
        state_with_sql = {
            **base_state,
            "generated_sql": "SELECT error_code, COUNT(*) FROM logs GROUP BY error_code",
        }
        result = validate_sql_node(state_with_sql)
        assert result.get("sql_validation_passed") is True
        assert result.get("validated_sql") is not None

    def test_validate_sql_blocks_dangerous_sql(self, base_state: GraphState) -> None:
        """validate_sql_node가 위험한 SQL에서 sql_validation_passed=False를 설정해야 한다."""
        state_with_bad_sql = {**base_state, "generated_sql": "DROP TABLE logs"}
        result = validate_sql_node(state_with_bad_sql)
        assert result.get("sql_validation_passed") is False
        assert len(result.get("errors", [])) > 0

    def test_execute_sql_skipped_when_validation_failed(self, base_state: GraphState) -> None:
        """SQL 검증 실패 시 execute_sql_node는 DB를 실행하지 않아야 한다."""
        state_invalid = {
            **base_state,
            "sql_validation_passed": False,
            "validated_sql": None,
        }
        result = execute_sql_node(state_invalid)
        # db_rows가 설정되지 않아야 함
        assert result.get("db_rows") is None or result.get("db_rows") == []

    def test_execute_sql_with_mock_db(self, base_state: GraphState) -> None:
        """Mock DB 연결로 execute_sql_node가 결과를 state에 저장해야 한다."""
        state_validated = {
            **base_state,
            "sql_validation_passed": True,
            "validated_sql": "SELECT error_code, COUNT(*) as cnt FROM logs GROUP BY error_code",
        }
        mock_result = {
            "columns": ["error_code", "cnt"],
            "rows": [["E1001", 42], ["E1002", 28]],
            "row_count": 2,
        }
        with patch("src.db_to_llm.stream.nodes.execute_sql_node.execute_sql") as mock_exec:
            mock_exec.return_value = mock_result
            result = execute_sql_node(state_validated)

        assert result.get("db_columns") == ["error_code", "cnt"]
        assert result.get("db_row_count") == 2

    def test_summarize_db_generates_summary(self, base_state: GraphState) -> None:
        """summarize_db_node가 db_summary를 생성해야 한다."""
        state_with_db = {
            **base_state,
            "db_columns": ["error_code", "cnt"],
            "db_rows": [["E1001", 42], ["E1002", 28]],
            "db_row_count": 2,
        }
        with (
            patch("src.db_to_llm.stream.nodes.summarize_db_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.summarize_db_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "요약 프롬프트"
            mock_gen.return_value = "E1001 오류가 42회로 가장 많이 발생했습니다."
            result = summarize_db_node(state_with_db)

        assert result.get("db_summary") is not None
        assert len(result["db_summary"]) > 0

    def test_retrieve_rag_with_db_summary(self, base_state: GraphState) -> None:
        """DB 요약이 있을 때 retrieve_rag_node가 DB+질문을 조합해 검색해야 한다."""
        state_with_summary = {
            **base_state,
            "db_summary": "E1001 오류가 42회로 가장 많이 발생했습니다.",
        }
        mock_contexts = [
            {"chunk_id": "c1", "text": "E1001 오류는 DB 연결 실패를 의미합니다.", "source": "doc.md", "score": 0.9}
        ]
        with patch("src.db_to_llm.stream.nodes.retrieve_rag_node.retrieve_contexts") as mock_ret:
            mock_ret.return_value = mock_contexts
            result = retrieve_rag_node(state_with_summary)

        assert result.get("retrieved_contexts") == mock_contexts
        # DB 요약이 있는 경우 조합된 쿼리로 호출되어야 함
        call_args = mock_ret.call_args
        query_arg = call_args[0][0]
        assert "E1001" in query_arg or "오류" in query_arg

    def test_final_answer_combines_all_info(self, base_state: GraphState) -> None:
        """final_answer_node가 DB 요약과 RAG 결과를 모두 합쳐 최종 답변을 생성해야 한다."""
        state_complete = {
            **base_state,
            "db_summary": "E1001 오류가 42회 발생했습니다.",
            "retrieved_contexts": [
                {"chunk_id": "c1", "text": "E1001은 DB 연결 오류입니다.", "source": "doc.md", "score": 0.9}
            ],
        }
        with (
            patch("src.db_to_llm.stream.nodes.final_answer_node.generate_text") as mock_gen,
            patch("src.db_to_llm.stream.nodes.final_answer_node.get_prompt_manager") as mock_pm,
        ):
            mock_pm.return_value.render.return_value = "최종 답변 프롬프트"
            mock_gen.return_value = "E1001 오류가 가장 많이 발생했으며, 이는 DB 연결 실패입니다."
            result = final_answer_node(state_complete)

        assert result.get("final_answer") is not None
        assert len(result["final_answer"]) > 0
