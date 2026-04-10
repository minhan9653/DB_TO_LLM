# 이 파일은 그래프 상태 보조 함수(append_trace/append_error)의 동작을 검증한다.
# 상태 리스트가 불변성 있게 누적되는지 확인해 노드 간 추적 정보 품질을 보장한다.
# 작은 유틸리티 회귀가 전체 디버깅 경험을 해치지 않도록 단위 테스트로 고정한다.
# 순수 함수 테스트라 외부 의존 없이 매우 빠르게 실행된다.

from __future__ import annotations

from db_to_llm.stream.nodes.node_helpers import append_error, append_trace


def test_append_trace_adds_message() -> None:
    """
    debug_trace에 메시지가 추가되는지 확인한다.
    """
    state = {"debug_trace": ["a"]}
    traces = append_trace(state, "b")
    assert traces == ["a", "b"]
    assert state["debug_trace"] == ["a"]


def test_append_error_adds_message() -> None:
    """
    errors에 메시지가 추가되는지 확인한다.
    """
    state = {"errors": ["e1"]}
    errors = append_error(state, "e2")
    assert errors == ["e1", "e2"]
    assert state["errors"] == ["e1"]

