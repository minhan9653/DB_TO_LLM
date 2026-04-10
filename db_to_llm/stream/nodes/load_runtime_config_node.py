# 이 파일은 그래프 실행 시작 시 공통 런타임 의존성을 로드하는 노드다.
# config, logger, prompt manager, llm client를 한 번만 초기화해 하위 노드가 재사용한다.
# 노드는 상태에 runtime/runtime_config를 저장해 서비스 계층 호출 준비를 완료한다.
# 설정 실패 시 예외를 숨기지 않고 상위 실행기로 전파해 즉시 원인을 확인할 수 있게 한다.

from __future__ import annotations

from db_to_llm.common.config.runtime_config import build_runtime_services
from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_trace

logger = get_logger(__name__)


def load_runtime_config_node(state: StreamGraphState) -> StreamGraphState:
    """
    런타임 의존성을 생성하고 상태에 저장한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: runtime 초기화 정보가 반영된 상태 조각.
    """
    runtime = build_runtime_services(config_path=state.get("config_path"))
    logger.info("load_runtime_config 노드 완료")
    return {
        "runtime": runtime,
        "runtime_config": runtime.config,
        "errors": list(state.get("errors", [])),
        "debug_trace": append_trace(state, "load_runtime_config_node"),
        "normalized_question": str(state.get("question", "")).strip(),
    }

