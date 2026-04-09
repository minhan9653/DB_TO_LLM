# 이 파일은 Root_Stream 설정 로더의 핵심 동작을 검증한다.
# 환경변수 오버라이드가 기대한 키에 반영되는지 확인한다.
# 파일 I/O는 임시 디렉터리에서만 수행해 테스트 재현성을 유지한다.
# 외부 네트워크/DB 의존 없이 단위 수준으로 검증한다.

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from Root_Stream.utils.config_loader import load_config


class ConfigLoaderTests(unittest.TestCase):
    """Root_Stream config loader 테스트."""

    def test_load_config_applies_env_overrides(self) -> None:
        config_path = Path(__file__).resolve().parent / "_runtime_config.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "mode: prompt_llm",
                    "llm_provider: ollama",
                    "ollama:",
                    "  model: base-model",
                    "  base_url: http://localhost:11434",
                    "openai:",
                    "  model: gpt-4.1-mini",
                    "  api_key: ''",
                    "database:",
                    "  host: 127.0.0.1",
                    "  port: 1433",
                    "  database: default_db",
                    "  username: default_user",
                    "  password: default_pass",
                    "logging:",
                    "  level: INFO",
                ]
            ),
            encoding="utf-8",
        )

        try:
            with patch.dict(
                os.environ,
                {
                    "STREAM_MODE": "rag_prompt_llm",
                    "LLM_PROVIDER": "openai",
                    "OPENAI_API_KEY": "env-key",
                    "DB_HOST": "10.0.0.10",
                    "DB_PORT": "1500",
                    "DB_NAME": "prod_db",
                    "DB_USER": "prod_user",
                    "DB_PASSWORD": "prod_pass",
                    "LOG_LEVEL": "DEBUG",
                },
                clear=False,
            ):
                loaded = load_config(config_path)
        finally:
            config_path.unlink(missing_ok=True)

        self.assertEqual(loaded["mode"], "rag_prompt_llm")
        self.assertEqual(loaded["llm_provider"], "openai")
        self.assertEqual(loaded["openai"]["api_key"], "env-key")
        self.assertEqual(loaded["database"]["host"], "10.0.0.10")
        self.assertEqual(loaded["database"]["port"], 1500)
        self.assertEqual(loaded["database"]["database"], "prod_db")
        self.assertEqual(loaded["database"]["username"], "prod_user")
        self.assertEqual(loaded["database"]["password"], "prod_pass")
        self.assertEqual(loaded["logging"]["level"], "DEBUG")


if __name__ == "__main__":
    unittest.main()
