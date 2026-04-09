# 이 파일은 Root_Stream 설정 파일(config.yaml)과 환경변수를 함께 로드한다.
# 기본값은 YAML에서 읽고, 배포/개발 환경별 차이는 환경변수로 덮어쓴다.
# 민감정보는 코드 하드코딩 대신 .env 또는 OS 환경변수로 주입하는 것을 기본으로 한다.
# 오케스트레이터/서버/CLI가 같은 로더를 재사용하도록 단일 진입점으로 유지한다.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from Root_Stream.utils.logger import get_logger

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
    _set_if_env(config, "mode", "STREAM_MODE")
    _set_if_env(config, "llm_provider", "LLM_PROVIDER")

    _set_nested_if_env(config, ("ollama", "model"), "OLLAMA_MODEL")
    _set_nested_if_env(config, ("ollama", "base_url"), "OLLAMA_BASE_URL")

    _set_nested_if_env(config, ("openai", "model"), "OPENAI_MODEL")
    _set_nested_if_env(config, ("openai", "api_key"), "OPENAI_API_KEY")

    _set_nested_if_env(config, ("logging", "level"), "LOG_LEVEL")

    _set_nested_if_env(config, ("database", "host"), "DB_HOST")
    _set_nested_if_env(config, ("database", "database"), "DB_NAME")
    _set_nested_if_env(config, ("database", "username"), "DB_USER")
    _set_nested_if_env(config, ("database", "password"), "DB_PASSWORD")
    _set_nested_if_env(config, ("database", "driver"), "DB_DRIVER")

    _set_nested_if_env(config, ("database", "port"), "DB_PORT", caster=int)
    _set_nested_if_env(config, ("database", "timeout"), "DB_TIMEOUT", caster=int)
    _set_nested_if_env(config, ("database", "encrypt"), "DB_ENCRYPT", caster=_parse_bool)
    _set_nested_if_env(
        config,
        ("database", "trust_server_certificate"),
        "DB_TRUST_SERVER_CERTIFICATE",
        caster=_parse_bool,
    )


def _set_if_env(config: dict[str, Any], key: str, env_name: str) -> None:
    """환경변수가 있으면 config 최상위 키를 덮어쓴다."""
    value = os.getenv(env_name)
    if value is not None and value != "":
        config[key] = value


def _set_nested_if_env(
    config: dict[str, Any],
    key_path: tuple[str, str],
    env_name: str,
    caster: type | None = None,
) -> None:
    """환경변수가 있으면 config 중첩 키를 덮어쓴다."""
    raw_value = os.getenv(env_name)
    if raw_value is None or raw_value == "":
        return

    value: Any = raw_value
    if caster is not None:
        try:
            value = caster(raw_value)
        except Exception as error:
            raise ValueError(f"환경변수 값 형식이 올바르지 않습니다: {env_name}={raw_value}") from error

    section, key = key_path
    config.setdefault(section, {})[key] = value


def _parse_bool(raw_value: str) -> bool:
    """문자열 bool 값을 파싱한다."""
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"지원하지 않는 bool 값입니다: {raw_value}")
