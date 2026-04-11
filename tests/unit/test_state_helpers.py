# 이 파일은 그래프 상태 보조 함수(append_trace/append_error)의 동작을 검증한다.
# 상태 리스트가 불변성 있게 누적되는지 확인해 노드 간 추적 정보 품질을 보장한다.

from __future__ import annotations

from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace


def test_append_trace_adds_message() -> None:
    """trace_logs에 메시지가 추가되는지 확인한다."""
    state = {"trace_logs": []}
    traces = append_trace(state, "테스트 메시지")
    assert len(traces) == 1
    assert "테스트 메시지" in traces[0]
    assert state["trace_logs"] == []  # 원본 불변


def test_append_trace_accumulates() -> None:
    """trace_logs에 여러 메시지가 누적되는지 확인한다."""
    state: dict = {}
    traces1 = append_trace(state, "첫 번째")
    state2 = {"trace_logs": traces1}
    traces2 = append_trace(state2, "두 번째")
    assert len(traces2) == 2


def test_append_error_adds_message() -> None:
    """errors에 메시지가 추가되는지 확인한다."""
    state = {"errors": []}
    errors = append_error(state, "오류 발생")
    assert len(errors) == 1
    assert "오류 발생" in errors[0]
    assert state["errors"] == []  # 원본 불변
