# 이 파일은 Stream 실행에 필요한 설정과 런타임 의존 객체를 한 번에 구성한다.
# 기존 Root_Stream의 config/prompt/llm 로직을 최대한 재사용하도록 얇은 래퍼로 유지한다.
# Graph 노드에서는 이 모듈이 만든 RuntimeServices만 참조해 구현 복잡도를 낮춘다.
# 외부 설정은 config 파일과 .env를 우선 사용하고 하드코딩을 피한다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.services.llm.llm_factory import create_llm_client
from Root_Stream.utils.config_loader import load_config
from Root_Stream.utils.path_utils import resolve_path
from db_to_llm.common.logging.logger import get_logger, setup_logger

logger = get_logger(__name__)

DEFAULT_STREAM_CONFIG = Path(__file__).resolve().parents[3] / "Root_Stream" / "config" / "config.yaml"
DEFAULT_STREAM_CONFIG_EXAMPLE = Path(__file__).resolve().parents[3] / "Root_Stream" / "config" / "config.example.yaml"


@dataclass
class RuntimeServices:
    """Graph 노드가 공통으로 사용하는 런타임 의존성을 묶는다."""

    config_path: Path
    config: dict[str, Any]
    project_root: Path
    prompt_manager: PromptManager
    llm_client: BaseLLMClient


def build_runtime_services(config_path: str | Path | None = None) -> RuntimeServices:
    """
    config를 로드하고 실행에 필요한 공통 의존성을 생성한다.

    Args:
        config_path: Stream config 파일 경로. 미지정 시 기본 경로 사용.

    Returns:
        RuntimeServices: Graph 실행 공통 의존성 묶음.
    """
    resolved_config_path = resolve_stream_config_path(config_path)
    config = load_config(resolved_config_path)
    stream_root = resolved_config_path.parent.parent
    project_root = resolve_path(config.get("paths", {}).get("project_root", "."), stream_root)
    _configure_logging(config=config, project_root=project_root)

    prompt_file_path = resolve_path(config["paths"]["prompt_file"], project_root)
    prompt_manager = PromptManager(prompt_file_path=prompt_file_path)
    llm_client = create_llm_client(config)

    logger.info("런타임 의존성 초기화 완료: config=%s", resolved_config_path)
    return RuntimeServices(
        config_path=resolved_config_path,
        config=config,
        project_root=project_root,
        prompt_manager=prompt_manager,
        llm_client=llm_client,
    )


def resolve_stream_config_path(config_path: str | Path | None = None) -> Path:
    """
    stream config 경로를 안전하게 해석한다.

    Args:
        config_path: 사용자가 지정한 config 경로.

    Returns:
        Path: 실제 사용할 config 경로.
    """
    candidate_path = Path(config_path or DEFAULT_STREAM_CONFIG).resolve()
    if candidate_path.exists():
        return candidate_path

    if candidate_path.name == "config.yaml":
        example_path = candidate_path.with_name("config.example.yaml")
        if example_path.exists():
            logger.warning(
                "config.yaml이 없어 config.example.yaml을 사용합니다: %s",
                example_path,
            )
            return example_path

    if not config_path and DEFAULT_STREAM_CONFIG_EXAMPLE.exists():
        logger.warning(
            "기본 config.yaml이 없어 config.example.yaml을 사용합니다: %s",
            DEFAULT_STREAM_CONFIG_EXAMPLE,
        )
        return DEFAULT_STREAM_CONFIG_EXAMPLE

    return candidate_path


def _configure_logging(*, config: dict[str, Any], project_root: Path) -> None:
    """
    config에 정의된 로깅 레벨/파일 경로를 기준으로 공통 logger를 설정한다.

    Args:
        config: 실행 config 데이터.
        project_root: 상대 경로 해석 기준 루트.
    """
    log_level = str(config.get("logging", {}).get("level", "INFO"))
    log_file_value = config.get("paths", {}).get("log_file")
    log_file_path = resolve_path(log_file_value, project_root) if log_file_value else None
    setup_logger(log_level=log_level, log_file_path=log_file_path)
