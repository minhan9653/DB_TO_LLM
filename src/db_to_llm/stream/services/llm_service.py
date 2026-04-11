# 이 파일은 LLM 클라이언트를 통일된 인터페이스로 호출하는 서비스 함수를 담는다.
# config를 받아 LLM 클라이언트를 생성하고 텍스트를 생성하는 단일 진입점이다.
# 모든 노드는 LLM 클라이언트를 직접 생성하지 않고 이 서비스를 통해 호출한다.
# 호출 전후 로그를 남겨 어느 노드에서 LLM을 호출했는지 추적할 수 있다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.shared.llm.llm_factory import create_llm_client
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


def generate_text(
    system_prompt: str,
    user_prompt: str,
    config: dict[str, Any],
    temperature: float = 0.0,
    caller_name: str = "unknown",
) -> str:
    """
    LLM을 호출해 텍스트를 생성한다.

    Args:
        system_prompt: LLM 역할/지침을 정의하는 시스템 프롬프트.
        user_prompt: 실제 생성 요청.
        config: load_config()로 읽은 전체 설정 dict.
        temperature: 응답 다양성 조절값.
        caller_name: 로그에 표시할 호출 노드 이름.

    Returns:
        str: LLM이 생성한 텍스트.
    """
    logger.info("LLM 호출 시작: caller=%s", caller_name)

    llm_client = create_llm_client(config)

    try:
        result = llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
    except Exception:
        logger.exception("LLM 호출 실패: caller=%s", caller_name)
        raise

    logger.info("LLM 호출 완료: caller=%s, output_length=%d", caller_name, len(result))
    return result
