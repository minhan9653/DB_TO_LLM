# 이 파일은 config 기반으로 LLM provider 구현체를 생성하는 팩토리 함수를 담는다.
# llm_provider 설정값에 따라 OllamaClient 또는 OpenAIClient를 반환한다.
# 새 provider를 추가할 때 이 파일만 수정하면 나머지 코드는 변경하지 않아도 된다.
# 모든 노드와 서비스는 직접 client를 생성하지 않고 이 팩토리를 통해 가져온다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.shared.llm.base_llm import BaseLLMClient
from src.db_to_llm.shared.llm.ollama_client import OllamaClient
from src.db_to_llm.shared.llm.openai_client import OpenAIClient
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


def create_llm_client(config: dict[str, Any]) -> BaseLLMClient:
    """
    config 설정에 따라 적절한 LLM 클라이언트를 생성해 반환한다.

    Args:
        config: load_config()로 읽은 전체 설정 dict.
                llm_provider, ollama, openai 섹션을 참조한다.

    Returns:
        BaseLLMClient: OllamaClient 또는 OpenAIClient 인스턴스.

    Raises:
        ValueError: 지원하지 않는 llm_provider 값이 설정된 경우 발생한다.
    """
    provider = str(config.get("llm_provider", "ollama")).strip().lower()
    logger.info("LLM 클라이언트 생성 시작: provider=%s", provider)

    if provider == "ollama":
        ollama_config = config.get("ollama", {})
        client = OllamaClient(
            model=str(ollama_config.get("model", "qwen2.5:14b")),
            base_url=str(ollama_config.get("base_url", "http://127.0.0.1:11434")),
            request_timeout=int(ollama_config.get("request_timeout", 60)),
        )
        logger.info("OllamaClient 생성 완료: model=%s", client.model)
        return client

    if provider == "openai":
        openai_config = config.get("openai", {})
        client = OpenAIClient(
            model=str(openai_config.get("model", "gpt-4.1-mini")),
            api_key=openai_config.get("api_key"),
            request_timeout=int(openai_config.get("request_timeout", 60)),
        )
        logger.info("OpenAIClient 생성 완료: model=%s", client.model)
        return client

    raise ValueError(
        f"지원하지 않는 llm_provider입니다: '{provider}'. 사용 가능한 값: ollama, openai"
    )
