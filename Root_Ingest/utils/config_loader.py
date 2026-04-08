# 이 파일은 설정 파일과 환경 변수를 읽는 역할을 합니다.

# 기본 설정은 config.yaml에서 읽고, 필요한 값만 .env로 덮어씁니다.

# 민감정보는 코드에 하드코딩하지 않고 환경 변수 사용을 전제로 둡니다.

# 설정 로딩 과정도 로그로 남겨 디버깅을 쉽게 합니다.

from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml
from Root_Ingest.utils.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path: Path) -> dict[str, Any]:
    """
    역할:
    INGEST 설정 로드에서 파일/설정을 읽어 메모리 객체로 변환합니다.
    
    Args:
    config_path (Path):
    역할: 로드할 설정 파일 위치를 지정합니다.
    값: `Path` 형식의 파일 경로입니다.
    전달 출처: CLI `--config` 값 또는 상위 실행 코드에서 전달됩니다.
    주의사항: 상대 경로일 때 실행 위치에 따라 다른 파일을 읽을 수 있어 `resolve()` 결과 확인이 필요합니다.
    
    Returns:
    dict[str, Any]: INGEST 설정 로드 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
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

    _apply_env_overrides(config)

    logger.info("설정 로드 완료")
    return config


def _safe_load_dotenv(config_path: Path) -> None:
    """
    역할:
    INGEST 설정 로드 문맥에서 `_safe_load_dotenv` 기능을 수행합니다.
    
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
    INGEST 설정 로드 문맥에서 `_apply_env_overrides` 기능을 수행합니다.
    
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

    embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")

    chroma_collection_name = os.getenv("CHROMA_COLLECTION_NAME")

    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR")

    log_level = os.getenv("LOG_LEVEL")
    if embedding_model_name:
        config.setdefault("embedding", {})["model_name"] = embedding_model_name

    if chroma_collection_name:
        config.setdefault("vector_store", {})["collection_name"] = chroma_collection_name

    if chroma_persist_dir:
        config.setdefault("paths", {})["chroma_dir"] = chroma_persist_dir

    if log_level:
        config.setdefault("logging", {})["level"] = log_level
