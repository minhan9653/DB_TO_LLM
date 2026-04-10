# 이 파일은 RuntimeServices 빌더가 설정/프롬프트/LLM 의존성을 묶어 생성하는지 검증한다.
# 임시 config와 임시 prompt 파일을 사용해 외부 시스템 없이 로더 동작을 확인한다.
# Graph 시작 노드가 rely하는 최소 런타임 계약이 깨지지 않도록 회귀 테스트를 제공한다.
# .env 하드코딩 없이 파일 기반 설정만으로 초기화 가능한지 함께 확인한다.

from __future__ import annotations

from pathlib import Path

from db_to_llm.common.config.runtime_config import build_runtime_services


def test_build_runtime_services_with_temp_config(tmp_path: Path) -> None:
    """
    임시 config 경로로 RuntimeServices 생성이 가능한지 확인한다.

    Args:
        tmp_path: pytest 임시 디렉터리.
    """
    prompt_file = tmp_path / "prompts.yaml"
    prompt_file.write_text(
        "\n".join(
            [
                "prompts:",
                "  default_system_prompt: |",
                "    system",
                "  query_generation_prompt: |",
                "    Q: {question}",
                "  rag_query_generation_prompt: |",
                "    R: {retrieved_context}",
                "  planner_system_prompt: |",
                "    planner system",
                "  planner_user_prompt: |",
                "    planner user {question}",
            ]
        ),
        encoding="utf-8",
    )

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "\n".join(
            [
                "mode: prompt_llm",
                "llm_provider: ollama",
                "paths:",
                "  project_root: .",
                f"  prompt_file: {prompt_file.name}",
                "ollama:",
                "  model: qwen2.5:7b",
                "  base_url: http://127.0.0.1:11434",
                "  request_timeout: 10",
                "openai:",
                "  model: gpt-4.1-mini",
                "  api_key: ''",
                "  request_timeout: 10",
                "retrieval:",
                "  enabled: false",
                "prompts:",
                "  active_prompt: query_generation_prompt",
                "logging:",
                "  level: INFO",
                "sql:",
                "  allow_only_select: true",
            ]
        ),
        encoding="utf-8",
    )

    runtime = build_runtime_services(config_file)
    assert runtime.config_path == config_file.resolve()
    assert runtime.config["mode"] == "prompt_llm"
    assert runtime.prompt_manager.get_prompt("default_system_prompt").strip() == "system"

