# 이 파일은 api_result mode 실행 로직을 담당합니다.

# 외부 API를 호출하고 응답에서 query 후보를 우선 추출합니다.

# query 추출이 어려운 경우 LLM 후처리 프롬프트로 query를 생성합니다.

# API 원본 응답은 StreamResult.raw_response로 보존해 추적 가능하게 합니다.

from __future__ import annotations
from typing import Any
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.api.external_api_service import ExternalApiService
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.stream.models import StreamRequest, StreamResult
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def run_api_result_mode(

    *,

    request: StreamRequest,

    config: dict[str, Any],

    prompt_manager: PromptManager,

    llm_client: BaseLLMClient,

) -> StreamResult:
    """
    역할:
    STREAM api_result 모드 흐름을 실행하고 후속 단계에서 사용할 결과를 조합해 반환합니다.
    
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

    logger.info("mode 실행 시작: api_result")

    api_config = config.get("api", {})

    endpoint = str(api_config.get("endpoint", "")).strip()
    if not endpoint:
        raise ValueError("api.endpoint 설정이 비어 있습니다.")

    api_service = ExternalApiService(

        endpoint=endpoint,

        timeout=int(api_config.get("timeout", 10)),

        method=str(api_config.get("method", "POST")),

        headers=api_config.get("headers", {}),

    )

    api_result = api_service.call(request.question)

    direct_query = api_service.extract_query(api_result)
    if direct_query:
        query = direct_query

        prompt_key = None

    else:
        logger.info("API 응답에서 query를 찾지 못해 LLM 후처리를 수행합니다.")

        prompt_key = "api_postprocess_prompt"

        system_prompt = prompt_manager.get_prompt("default_system_prompt")

        user_prompt = prompt_manager.render_prompt(

            prompt_key,

            {

                "question": request.question,

                "api_result": api_service.stringify(api_result),

            },

        )

        query = llm_client.generate(system_prompt=system_prompt, user_prompt=user_prompt)

    result = StreamResult(

        mode="api_result",

        question=request.question,

        query=query,

        llm_provider=llm_client.provider_name if prompt_key else None,

        prompt_key=prompt_key,

        raw_response=api_result,

        metadata={

            "mode": config.get("mode"),

            "api_endpoint": endpoint,

        },

    )

    logger.info("mode 실행 완료: api_result")
    return result
