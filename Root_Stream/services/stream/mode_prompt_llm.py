# 이 파일은 prompt_llm mode 실행 로직을 담당합니다.

# 사용자 질문과 사전 정의된 프롬프트 템플릿을 결합해 query를 생성합니다.

# 활성 프롬프트 키는 config.prompts.active_prompt에서 읽습니다.

# 프롬프트 선택 정보는 결과에 포함해 추적 가능하게 유지합니다.

from __future__ import annotations
from typing import Any
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.stream.models import StreamRequest, StreamResult
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def run_prompt_llm_mode(

    *,

    request: StreamRequest,

    config: dict[str, Any],

    prompt_manager: PromptManager,

    llm_client: BaseLLMClient,

) -> StreamResult:
    """
    역할:
    STREAM prompt_llm 모드 흐름을 실행하고 후속 단계에서 사용할 결과를 조합해 반환합니다.
    
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
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("mode 실행 시작: prompt_llm")

    prompts_config = config.get("prompts", {})

    prompt_key = str(prompts_config.get("active_prompt", "query_generation_prompt"))

    system_prompt = prompt_manager.get_prompt("default_system_prompt")

    user_prompt = prompt_manager.render_prompt(prompt_key, {"question": request.question})

    query = llm_client.generate(system_prompt=system_prompt, user_prompt=user_prompt)

    result = StreamResult(

        mode="prompt_llm",

        question=request.question,

        query=query,

        llm_provider=llm_client.provider_name,

        prompt_key=prompt_key,

        metadata={

            "mode": config.get("mode"),

            "llm_provider": config.get("llm_provider"),

        },

    )

    logger.info("mode 실행 완료: prompt_llm")
    return result
