# 이 파일은 질문 1건 입력 시 Planner부터 최종 응답까지 전체 흐름을 검증하는 e2e 테스트다.
# 외부 시스템(LLM/DB/RAG)은 모두 fixture와 모킹으로 대체해 오프라인 재현성을 보장한다.
# 핵심 검증 포인트는 planner->route->sql->validate->execute->final 순서 유지다.
# CLI/API가 재사용하는 동일 graph runner 기준으로 테스트해 실제 실행 경로를 보호한다.

from __future__ import annotations

import json
from pathlib import Path

from db_to_llm.stream.graph.runner import run_stream_graph


def test_end_to_end_workflow_with_mocks(
    monkeypatch,
    fixture_root: Path,
    sample_sql: str,
    sample_db_rows,
    sample_rag_contexts,
) -> None:
    """
    Planner부터 final_response까지 전체 흐름이 모의 객체 기반으로 동작하는지 확인한다.

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
            "reasoning_summary": "mocked",
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
        lambda **kwargs: {"final_answer": "최종 응답", "errors": []},
    )

    result = run_stream_graph(
        question="최근 24시간 에러 요약과 관련 문서 알려줘",
        mode="auto",
        execute_sql=True,
    )
    payload = result.payload

    assert payload["question"] == "최근 24시간 에러 요약과 관련 문서 알려줘"
    assert payload["query_type"] == "DB_THEN_RAG"
    assert payload["generated_sql"]
    assert payload["sql_validation_result"]["is_valid"] is True
    assert payload["execution_result"]["row_count"] == len(sample_db_rows)
    assert payload["final_answer"] == "최종 응답"
    assert payload["errors"] == []

    expected_steps = [
        "load_runtime_config_node",
        "planner_node",
        "rag_retrieve_node",
        "rag_prompt_llm_node",
        "sql_validation_node",
        "db_execute_node",
        "result_summary_node",
        "final_response_node",
    ]
    assert payload["debug_trace"] == expected_steps

