# 이 파일은 STREAM 설정 파일과 환경 변수를 로딩하는 역할을 담당합니다.

# 기본 설정은 config.yaml에서 읽고, 필요한 값만 환경 변수로 덮어씁니다.

# 민감 정보(API Key)는 코드 하드코딩 대신 환경 변수 사용을 기본으로 합니다.

# 설정 로딩 과정도 로깅해 실행 시점의 설정 상태를 추적할 수 있게 합니다.

from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path: Path) -> dict[str, Any]:
    """
    역할:
    STREAM 설정 로드에서 파일/설정을 읽어 메모리 객체로 변환합니다.
    
    Args:
    config_path (Path):
    역할: 로드할 설정 파일 위치를 지정합니다.
    값: `Path` 형식의 파일 경로입니다.
    전달 출처: CLI `--config` 값 또는 상위 실행 코드에서 전달됩니다.
    주의사항: 상대 경로일 때 실행 위치에 따라 다른 파일을 읽을 수 있어 `resolve()` 결과 확인이 필요합니다.
    
    Returns:
    dict[str, Any]: STREAM 설정 로드 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
    Raises:
    FileNotFoundError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    logger.info("설정 로드 시작: %s", config_path)
    if not config_path.exists():
        logger.error("설정 파일을 찾을 수 없습니다: %s", config_path)

        raise FileNotFoundError(f"설정 파일이 없습니다: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config: dict[str, Any] = yaml.safe_load(file) or {}

    _safe_load_dotenv(config_path)
    # 환경 변수 오버라이드는 명시적으로 호출하여 어떤 값이 덮어씌워졌는지 로그에 남길 수 있게 합니다.
    _apply_env_overrides(config)

    logger.info("설정 로드 완료")
    return config


def _safe_load_dotenv(config_path: Path) -> None:
    """
    역할:
    STREAM 설정 로드 문맥에서 `_safe_load_dotenv` 기능을 수행합니다.
    
    Args:
    config_path (Path):
    역할: 로드할 설정 파일 위치를 지정합니다.
    값: `Path` 형식의 파일 경로입니다.
    전달 출처: CLI `--config` 값 또는 상위 실행 코드에서 전달됩니다.
    주의사항: 상대 경로일 때 실행 위치에 따라 다른 파일을 읽을 수 있어 `resolve()` 결과 확인이 필요합니다.
    
    Returns:
    None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    dotenv_path = config_path.parent.parent / ".env"
    try:
        from dotenv import load_dotenv

    except Exception:
        logger.warning("python-dotenv 모듈이 없어 .env 로드를 건너뜁니다.")
        return

    load_dotenv(dotenv_path=dotenv_path, override=False)


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """
    역할:
    STREAM 설정 로드 문맥에서 `_apply_env_overrides` 기능을 수행합니다.
    
    Args:
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    
    Returns:
    None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    mode = os.getenv("STREAM_MODE")

    llm_provider = os.getenv("LLM_PROVIDER")

    ollama_model = os.getenv("OLLAMA_MODEL")

    ollama_base_url = os.getenv("OLLAMA_BASE_URL")

    openai_model = os.getenv("OPENAI_MODEL")

    openai_api_key = os.getenv("OPENAI_API_KEY")

    log_level = os.getenv("LOG_LEVEL")
    if mode:
        config["mode"] = mode

    if llm_provider:
        config["llm_provider"] = llm_provider

    if ollama_model:
        config.setdefault("ollama", {})["model"] = ollama_model

    if ollama_base_url:
        config.setdefault("ollama", {})["base_url"] = ollama_base_url

    if openai_model:
        config.setdefault("openai", {})["model"] = openai_model

    if openai_api_key:
        config.setdefault("openai", {})["api_key"] = openai_api_key

    if log_level:
        config.setdefault("logging", {})["level"] = log_level
