# 이 파일은 여러 노드에서 공통으로 쓰는 상태 갱신 유틸리티를 제공한다.
# debug_trace와 errors 리스트 갱신 규칙을 한 곳에서 관리해 중복을 줄인다.
# 노드 함수는 핵심 비즈니스 호출에 집중하고 부가 상태 처리는 헬퍼로 위임한다.
# 테스트에서 상태 갱신 규칙을 독립적으로 검증할 수 있도록 순수 함수로 유지한다.

from __future__ import annotations

from db_to_llm.common.config.runtime_config import RuntimeServices
from db_to_llm.stream.graph.state import StreamGraphState


def get_runtime(state: StreamGraphState) -> RuntimeServices:
    """
    상태에서 runtime을 안전하게 꺼낸다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        RuntimeServices: 초기화된 런타임 의존성 객체.

    Raises:
        RuntimeError: load_runtime_config_node가 실행되지 않아 runtime이 없을 때.
    """
    runtime = state.get("runtime")
    if runtime is None:
        raise RuntimeError("runtime이 초기화되지 않았습니다. load_runtime_config_node가 먼저 실행되어야 합니다.")
    return runtime


def append_trace(state: StreamGraphState, message: str) -> list[str]:
    """
    상태의 debug_trace에 메시지를 추가한 새 리스트를 반환한다.

    Args:
        state: 현재 그래프 상태.
        message: 추가할 추적 메시지.

    Returns:
        list[str]: 업데이트된 debug_trace.
    """
    traces = list(state.get("debug_trace", []))
    traces.append(message)
    return traces


def append_error(state: StreamGraphState, error_message: str) -> list[str]:
    """
    상태의 errors에 오류 메시지를 추가한 새 리스트를 반환한다.

    Args:
        state: 현재 그래프 상태.
        error_message: 기록할 오류 메시지.

    Returns:
        list[str]: 업데이트된 errors 리스트.
    """
    errors = list(state.get("errors", []))
    errors.append(error_message)
    return errors

