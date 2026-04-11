# 이 파일은 모든 노드에서 공통으로 사용하는 유틸리티 함수를 담는다.
# 현재 시각 계산, trace_logs 추가, errors 추가 함수를 제공한다.
# 각 노드는 중복 코드 없이 이 파일의 함수를 통해 상태를 업데이트한다.
# config를 인자로 받아 각 노드에서 공통 설정에 접근하는 방법도 여기에 정리한다.

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from src.db_to_llm.shared.config.config_loader import load_config
from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState

logger = get_logger(__name__)


def get_config(state: GraphState) -> dict[str, Any]:
    """
    state에서 config_path를 읽어 config dict를 로드한다.
    config_path가 없으면 기본 config/config.yaml을 사용한다.

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        dict: 로드된 설정 dict.
    """
    # 테스트 환경에서 config dict를 직접 주입할 수 있도록 _config_override 키를 먼저 확인한다.
    override = state.get("_config_override")
    if isinstance(override, dict):
        return override

    config_path_str = state.get("config_path", "")
    config_path = Path(config_path_str) if config_path_str else None
    return load_config(config_path)


def append_trace(state: GraphState, message: str) -> list[str]:
    """
    trace_logs에 새 메시지를 추가한 새 리스트를 반환한다.
    LangGraph는 불변 업데이트를 권장하므로 리스트를 복사해 반환한다.

    Args:
        state: 현재 상태.
        message: 추가할 추적 메시지.

    Returns:
        list[str]: 메시지가 추가된 새 trace_logs 리스트.
    """
    existing = list(state.get("trace_logs", []))
    existing.append(f"[{_now()}] {message}")
    return existing


def append_error(state: GraphState, error_message: str) -> list[str]:
    """
    errors에 새 오류 메시지를 추가한 새 리스트를 반환한다.

    Args:
        state: 현재 상태.
        error_message: 추가할 오류 메시지.

    Returns:
        list[str]: 오류 메시지가 추가된 새 errors 리스트.
    """
    existing = list(state.get("errors", []))
    existing.append(f"[{_now()}] {error_message}")
    return existing


def _now() -> str:
    """현재 시각을 'HH:MM:SS' 형식으로 반환한다."""
    return time.strftime("%H:%M:%S")
