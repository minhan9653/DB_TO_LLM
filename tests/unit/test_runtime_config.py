# 이 파일은 설정 로더(load_config)의 기본 동작을 검증한다.
# 임시 config 파일을 사용해 외부 시스템 없이 로더 동작을 확인한다.
# 필수 키 반환 및 FileNotFoundError 처리를 회귀 테스트로 고정한다.

from __future__ import annotations

from pathlib import Path

import pytest

from src.db_to_llm.shared.config.config_loader import load_config


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    """
    임시 config YAML을 읽어 dict를 반환하는지 확인한다.

    Args:
        tmp_path: pytest 임시 디렉터리.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "\n".join([
            "llm_provider: ollama",
            "ollama:",
            "  model: qwen2.5:7b",
            "  base_url: http://127.0.0.1:11434",
            "database:",
            "  host: localhost",
            "  port: 1433",
        ]),
        encoding="utf-8",
    )

    config = load_config(config_file)
    assert config["llm_provider"] == "ollama"
    assert config["ollama"]["model"] == "qwen2.5:7b"
    assert config["database"]["host"] == "localhost"


def test_load_config_raises_when_missing(tmp_path: Path) -> None:
    """
    존재하지 않는 config 경로에서 FileNotFoundError가 발생하는지 확인한다.

    Args:
        tmp_path: pytest 임시 디렉터리.
    """
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.yaml")
