# 이 파일은 config 기반으로 LLM provider 구현체를 생성하는 팩토리입니다.

# 오케스트레이터가 provider 분기 코드를 직접 갖지 않도록 책임을 분리합니다.

# 기본값은 ollama이며, openai는 선택적으로 활성화할 수 있습니다.

# provider 유효성 검증을 중앙에서 처리해 에러 메시지를 일관화합니다.

from __future__ import annotations
from typing import Any
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.services.llm.ollama_client import OllamaClient
from Root_Stream.services.llm.openai_client import OpenAIClient


def create_llm_client(config: dict[str, Any]) -> BaseLLMClient:
    """
    역할:
    LLM 클라이언트 생성 단계의 신규 산출물을 생성합니다.
    
    Args:
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    
    Returns:
    BaseLLMClient: LLM 클라이언트 생성 계산 결과를 `BaseLLMClient` 타입으로 반환합니다.
    
    Raises:
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    provider = str(config.get("llm_provider", "ollama")).strip().lower()
    if provider == "ollama":
        ollama_config = config.get("ollama", {})
        return OllamaClient(

            model=str(ollama_config.get("model", "qwen2.5:7b")),

            base_url=str(ollama_config.get("base_url", "http://localhost:11434")),

            request_timeout=int(ollama_config.get("request_timeout", 60)),

        )

    if provider == "openai":
        openai_config = config.get("openai", {})
        return OpenAIClient(

            model=str(openai_config.get("model", "gpt-4.1-mini")),

            api_key=openai_config.get("api_key"),

            request_timeout=int(openai_config.get("request_timeout", 60)),

        )

    raise ValueError(f"지원하지 않는 llm_provider입니다: {provider}. 사용 가능: ollama, openai")
