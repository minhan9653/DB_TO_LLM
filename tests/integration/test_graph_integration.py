# 이 파일은 LangGraph 노드 조합이 의도한 분기와 상태 업데이트를 수행하는지 통합 테스트한다.
# 외부 LLM/DB/RAG 호출은 monkeypatch로 모킹해 네트워크 없이 재현 가능하게 유지한다.
# prompt_llm/rag_prompt_llm 분기와 execute_sql True/False 분기를 모두 검증한다.
# 그래프 단위 회귀를 빠르게 잡기 위한 핵심 통합 시나리오를 포함한다.

from __future__ import annotations

import json
from pathlib import Path

from db_to_llm.stream.graph.runner import run_stream_graph


def test_prompt_flow_without_db_execution(
    monkeypatch,
    fixture_root: Path,
    sample_sql: str,
) -> None:
    """
    DB_ONLY + execute_sql=False 흐름에서 prompt 경로가 동작하는지 검증한다.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        fixture_root: fixture 루트 경로.
        sample_sql: 샘플 SQL fixture.
    """
    planner_payload = json.loads((fixture_root / "planner" / "sample_plan_db_only.json").read_text(encoding="utf-8"))

    monkeypatch.setattr(
        "db_to_llm.stream.nodes.planner_node.run_planner",
        lambda question, config_path: {
            "planner_raw": json.dumps(planner_payload, ensure_ascii=False),
            "planner_result": planner_payload,
            "query_type": planner_payload["query_type"],
            "reasoning_summary": "db only",
        },
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.prompt_llm_node.generate_text",
        lambda **kwargs: sample_sql,
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.final_response_node.generate_final_response",
        lambda **kwargs: {"final_answer": "ok", "errors": []},
    )

    result = run_stream_graph(
        question="장비별 에러 건수 알려줘",
        mode="auto",
        execute_sql=False,
    )
    payload = result.payload

    assert payload["mode"] == "prompt_llm"
    assert payload["query_type"] == "DB_ONLY"
    assert payload["generated_sql"]
    assert payload["sql_validation_result"]["is_valid"] is True
    assert payload["execution_result"]["row_count"] == 0
    assert "prompt_llm_node" in payload["debug_trace"]
    assert "db_execute_node" not in payload["debug_trace"]


def test_rag_flow_with_db_execution(
    monkeypatch,
    fixture_root: Path,
    sample_sql: str,
    sample_db_rows,
    sample_rag_contexts,
) -> None:
    """
    DB_THEN_RAG + execute_sql=True 흐름에서 rag/db 분기가 동작하는지 검증한다.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        fixture_root: fixture 루트 경로.
        sample_sql: 샘플 SQL fixture.
        sample_db_rows: 샘플 DB rows.
        sample_rag_contexts: 샘플 RAG contexts.
    """
    planner_payload = json.loads((fixture_root / "planner" / "sample_plan_db_then_rag.json").read_text(encoding="utf-8"))

    monkeypatch.setattr(
        "db_to_llm.stream.nodes.planner_node.run_planner",
        lambda question, config_path: {
            "planner_raw": json.dumps(planner_payload, ensure_ascii=False),
            "planner_result": planner_payload,
            "query_type": planner_payload["query_type"],
            "reasoning_summary": "db then rag",
        },
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.rag_retrieve_node.retrieve_contexts",
        lambda **kwargs: sample_rag_contexts,
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.rag_prompt_llm_node.generate_text",
        lambda **kwargs: sample_sql,
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.db_execute_node.execute_sql",
        lambda **kwargs: {
            "columns": ["EQPID", "error_count"],
            "row_count": len(sample_db_rows),
            "rows": sample_db_rows,
        },
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.final_response_node.generate_final_response",
        lambda **kwargs: {"final_answer": "final", "errors": []},
    )

    result = run_stream_graph(
        question="최근 에러와 관련 문서까지 요약해줘",
        mode="auto",
        execute_sql=True,
    )
    payload = result.payload

    assert payload["mode"] == "rag_prompt_llm"
    assert payload["query_type"] == "DB_THEN_RAG"
    assert payload["sql_validation_result"]["is_valid"] is True
    assert payload["execution_result"]["row_count"] == len(sample_db_rows)
    assert payload["db_summary"]["row_count"] == len(sample_db_rows)
    assert payload["retrieved_context"]
    assert "rag_retrieve_node" in payload["debug_trace"]
    assert "db_execute_node" in payload["debug_trace"]
    assert "result_summary_node" in payload["debug_trace"]


def test_natural_flow_without_sql_execution(
    monkeypatch,
    fixture_root: Path,
    sample_sql: str,
) -> None:
    """
    GENERAL 쿼리에서 natural_llm 경로가 선택되는지 검증한다.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        fixture_root: fixture 루트 경로.
        sample_sql: 샘플 SQL fixture.
    """
    planner_payload = {
        "is_composite": False,
        "query_type": "GENERAL",
        "steps": [{"step": 1, "type": "general", "goal": "일반 답변", "depends_on": []}],
    }
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.planner_node.run_planner",
        lambda question, config_path: {
            "planner_raw": json.dumps(planner_payload, ensure_ascii=False),
            "planner_result": planner_payload,
            "query_type": "GENERAL",
            "reasoning_summary": "general",
        },
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.natural_llm_node.generate_text",
        lambda **kwargs: sample_sql,
    )
    monkeypatch.setattr(
        "db_to_llm.stream.nodes.final_response_node.generate_final_response",
        lambda **kwargs: {"final_answer": "general ok", "errors": []},
    )

    result = run_stream_graph(
        question="일반 질의",
        mode="auto",
        execute_sql=False,
    )
    payload = result.payload
    assert payload["mode"] == "natural_llm"
    assert payload["query_type"] == "GENERAL"
    assert payload["sql_validation_result"]["is_valid"] is True
    assert "natural_llm_node" in payload["debug_trace"]
