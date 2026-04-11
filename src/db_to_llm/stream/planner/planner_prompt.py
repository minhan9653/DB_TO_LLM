# 이 파일은 Planner용 system/user 프롬프트를 생성하는 역할을 담당한다.
# PromptManager에서 planner_system_prompt와 planner_user_prompt 키를 조회한다.
# PlannerService가 LLM 호출 전에 이 함수를 통해 완성된 프롬프트를 받는다.
# 프롬프트 내용은 prompt_templates.yaml에서 관리하며 이 파일은 조립만 담당한다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.prompts.prompt_manager import PromptManager

logger = get_logger(__name__)


def build_planner_prompts(
    question: str,
    prompt_manager: PromptManager,
) -> tuple[str, str]:
    """
    질문을 받아 Planner LLM 호출에 사용할 (system_prompt, user_prompt) 쌍을 반환한다.

    Args:
        question: 사용자의 원본 질문.
        prompt_manager: 프롬프트 키를 조회할 PromptManager 인스턴스.

    Returns:
        tuple[str, str]: (system_prompt, user_prompt) 쌍.

    Raises:
        KeyError: 프롬프트 키가 없는 경우 발생한다.
    """
    logger.info("Planner 프롬프트 생성 시작: question_length=%d", len(question))

    system_prompt = prompt_manager.get_prompt("planner_system_prompt")
    user_prompt = prompt_manager.render_prompt(
        "planner_user_prompt",
        values={"question": question},
    )

    logger.info("Planner 프롬프트 생성 완료")
    return system_prompt, user_prompt
