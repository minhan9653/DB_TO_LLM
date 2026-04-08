# 이 파일은 natural_llm mode 실행 로직을 담당합니다.

# 사용자 질문을 최소 전처리 후 LLM에 전달해 query를 생성합니다.

# 프롬프트 키/LLM provider 정보는 결과 메타데이터에 포함합니다.

# 다른 mode와 동일한 StreamResult 포맷으로 반환합니다.

from __future__ import annotations
from typing import Any
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.stream.models import StreamRequest, StreamResult
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def run_natural_llm_mode(

    *,

    request: StreamRequest,

    config: dict[str, Any],

    prompt_manager: PromptManager,

    llm_client: BaseLLMClient,

) -> StreamResult:
    """
    역할:
    STREAM natural_llm 모드 흐름을 실행하고 후속 단계에서 사용할 결과를 조합해 반환합니다.
    
    Args:
    request (StreamRequest):
    역할: 사용자 질문을 포함한 STREAM 요청 모델입니다.
    값: `StreamRequest` 인스턴스입니다.
    전달 출처: `StreamOrchestrator.run()` 또는 테스트 코드에서 생성되어 전달됩니다.
    주의사항: `request.question`이 비어 있으면 하위 모드에서 오류가 날 수 있습니다.
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    prompt_manager (PromptManager):
    역할: 프롬프트 키 조회와 템플릿 렌더링을 수행합니다.
    값: `PromptManager` 인스턴스입니다.
    전달 출처: `build_stream_orchestrator()`에서 생성되어 전달됩니다.
    주의사항: 템플릿 변수 누락 시 `KeyError`가 발생할 수 있습니다.
    llm_client (BaseLLMClient):
    역할: 모델 provider별 텍스트 생성을 수행합니다.
    값: `BaseLLMClient` 구현체(`OllamaClient`/`OpenAIClient`)입니다.
    전달 출처: `create_llm_client(config)` 결과가 전달됩니다.
    주의사항: 모델명, 엔드포인트, API 키 설정이 맞지 않으면 호출 예외가 전파됩니다.
    
    Returns:
    StreamResult: query, metadata, retrieved_context를 포함한 STREAM 표준 결과를 반환합니다.
    
    Raises:
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    logger.info("mode 실행 시작: natural_llm")

    system_prompt = prompt_manager.get_prompt("default_system_prompt")

    user_prompt = request.question.strip()
    if not user_prompt:
        raise ValueError("question이 비어 있습니다.")

    query = llm_client.generate(system_prompt=system_prompt, user_prompt=user_prompt)

    result = StreamResult(

        mode="natural_llm",

        question=request.question,

        query=query,

        llm_provider=llm_client.provider_name,

        prompt_key="default_system_prompt",

        metadata={

            "mode": config.get("mode"),

            "llm_provider": config.get("llm_provider"),

        },

    )

    logger.info("mode 실행 완료: natural_llm")
    return result
