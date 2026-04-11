# 이 파일은 프로젝트 전체 공통 설정을 YAML 파일과 환경변수에서 읽어 반환한다.
# 기본값은 config.yaml에서 읽고, 배포 환경별 차이는 환경변수로 덮어쓴다.
# 민감정보(DB 계정, API Key)는 .env 또는 OS 환경변수로 주입한다.
# 이 파일 하나를 모든 모듈(ingest, stream, planner)이 공통으로 재사용한다.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# 프로젝트 루트 기준 기본 설정 파일 경로
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config" / "config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    YAML 설정 파일을 읽고 환경변수 오버라이드를 적용한 설정 dict를 반환한다.

    Args:
        config_path: 설정 파일 경로. None이면 config/config.yaml을 자동으로 찾는다.

    Returns:
        dict[str, Any]: stream, ingest, db, llm, retrieval, logging 섹션을 담은 설정 dict.

    Raises:
        FileNotFoundError: 설정 파일이 없을 때 발생한다.
    """
    resolved_path = config_path or DEFAULT_CONFIG_PATH
    logger.info("설정 로드 시작: %s", resolved_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"설정 파일이 없습니다: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as file:
        config: dict[str, Any] = yaml.safe_load(file) or {}

    _safe_load_dotenv(resolved_path)
    _apply_env_overrides(config)

    logger.info("설정 로드 완료")
    return config


def _safe_load_dotenv(config_path: Path) -> None:
    """프로젝트 루트의 .env 파일을 읽어 환경변수로 등록한다."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("python-dotenv가 없어 .env 로드를 건너뜁니다.")
        return

    # 프로젝트 루트에서 .env 파일을 탐색
    candidates = [
        config_path.resolve().parents[4] / ".env",
        config_path.resolve().parents[3] / ".env",
    ]
    for dotenv_path in candidates:
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)
            logger.info(".env 로드 완료: %s", dotenv_path)
            return


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """정의된 환경변수 값을 config dict에 반영한다."""
    # LLM 설정
    _set_top_level_if_env(config, "llm_provider", "LLM_PROVIDER")
    _set_nested_if_env(config, ("ollama", "model"), "OLLAMA_MODEL")
    _set_nested_if_env(config, ("ollama", "base_url"), "OLLAMA_BASE_URL")
    _set_nested_if_env(config, ("openai", "model"), "OPENAI_MODEL")
    _set_nested_if_env(config, ("openai", "api_key"), "OPENAI_API_KEY")

    # 로깅 설정
    _set_nested_if_env(config, ("logging", "level"), "LOG_LEVEL")

    # DB 설정
    _set_nested_if_env(config, ("database", "host"), "DB_HOST")
    _set_nested_if_env(config, ("database", "port"), "DB_PORT", caster=int)
    _set_nested_if_env(config, ("database", "database"), "DB_NAME")
    _set_nested_if_env(config, ("database", "username"), "DB_USER")
    _set_nested_if_env(config, ("database", "password"), "DB_PASSWORD")
    _set_nested_if_env(config, ("database", "driver"), "DB_DRIVER")
    _set_nested_if_env(config, ("database", "timeout"), "DB_TIMEOUT", caster=int)
    _set_nested_if_env(config, ("database", "encrypt"), "DB_ENCRYPT", caster=_parse_bool)
    _set_nested_if_env(
        config,
        ("database", "trust_server_certificate"),
        "DB_TRUST_SERVER_CERTIFICATE",
        caster=_parse_bool,
    )


def _set_top_level_if_env(config: dict[str, Any], key: str, env_name: str) -> None:
    """환경변수가 있으면 config 최상위 키를 덮어쓴다."""
    value = os.getenv(env_name)
    if value:
        config[key] = value


def _set_nested_if_env(
    config: dict[str, Any],
    key_path: tuple[str, str],
    env_name: str,
    caster: type | None = None,
) -> None:
    """환경변수가 있으면 config의 중첩 키(섹션.키)를 덮어쓴다."""
    raw_value = os.getenv(env_name)
    if not raw_value:
        return

    value: Any = raw_value
    if caster is not None:
        try:
            value = caster(raw_value)
        except Exception as error:
            raise ValueError(
                f"환경변수 값 형식이 올바르지 않습니다: {env_name}={raw_value}"
            ) from error

    section, key = key_path
    config.setdefault(section, {})[key] = value


def _parse_bool(raw_value: str) -> bool:
    """'true'/'false' 형태의 문자열을 bool로 변환한다."""
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"bool로 변환할 수 없는 값입니다: {raw_value}")
