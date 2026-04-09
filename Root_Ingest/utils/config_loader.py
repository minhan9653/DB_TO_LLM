# 이 파일은 Root_Ingest 설정 파일(config.yaml)과 환경변수를 함께 로드한다.
# 기본값은 YAML에서 읽고, 환경별 변경값은 환경변수로 덮어쓴다.
# 인제스트 파이프라인/노트북이 같은 로더를 재사용하도록 단일 진입점을 제공한다.
# 민감정보와 경로 차이는 .env 또는 OS 환경변수로 주입하는 방식을 기본으로 한다.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from Root_Ingest.utils.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path: Path) -> dict[str, Any]:
    """config 파일을 읽고 환경변수 오버라이드를 적용한다."""
    logger.info("설정 로드 시작: %s", config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일이 없습니다: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config: dict[str, Any] = yaml.safe_load(file) or {}

    _safe_load_dotenv(config_path)
    _apply_env_overrides(config)
    logger.info("설정 로드 완료")
    return config


def _safe_load_dotenv(config_path: Path) -> None:
    """프로젝트 루트(.env)를 읽어 환경변수로 로드한다."""
    try:
        from dotenv import load_dotenv
    except Exception:
        logger.warning("python-dotenv 모듈이 없어 .env 로드를 건너뜁니다.")
        return
    repo_root_dotenv = config_path.resolve().parents[2] / ".env"
    module_dotenv = config_path.resolve().parents[1] / ".env"
    if repo_root_dotenv.exists():
        load_dotenv(dotenv_path=repo_root_dotenv, override=False)
    elif module_dotenv.exists():
        load_dotenv(dotenv_path=module_dotenv, override=False)


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """정의된 환경변수 값을 config dict에 반영한다."""
    _set_nested_if_env(config, ("embedding", "model_name"), "EMBEDDING_MODEL_NAME")
    _set_nested_if_env(config, ("vector_store", "collection_name"), "CHROMA_COLLECTION_NAME")
    _set_nested_if_env(config, ("paths", "chroma_dir"), "CHROMA_PERSIST_DIR")
    _set_nested_if_env(config, ("logging", "level"), "LOG_LEVEL")


def _set_nested_if_env(config: dict[str, Any], key_path: tuple[str, str], env_name: str) -> None:
    """환경변수가 있으면 config 중첩 키를 덮어쓴다."""
    value = os.getenv(env_name)
    if value is None or value == "":
        return
    section, key = key_path
    config.setdefault(section, {})[key] = value
