# 이 파일은 Planner 단계에서 사용할 프롬프트 조합 로직을 담당한다.
# 프롬프트 문자열은 Root_Stream/prompts/prompt_templates.yaml에서만 읽는다.
# PlannerService는 이 모듈을 통해 시스템/사용자 프롬프트를 얻어 LLM을 호출한다.
# 질문 바인딩 규칙을 중앙화해 테스트/노트북/디버그 실행의 일관성을 유지한다.

from __future__ import annotations

from Root_Stream.prompts.prompt_manager import PromptManager

PLANNER_SYSTEM_PROMPT_KEY = "planner_system_prompt"
PLANNER_USER_PROMPT_KEY = "planner_user_prompt"


def build_planner_prompts(*, prompt_manager: PromptManager, question: str) -> tuple[str, str]:
    """
    Planner용 system/user 프롬프트를 템플릿에서 렌더링한다.

    Args:
        prompt_manager: prompt_templates.yaml을 로드한 PromptManager 인스턴스.
        question: 사용자 질문 문자열.

    Returns:
        tuple[str, str]: (system_prompt, user_prompt)

    Raises:
        ValueError: 질문이 비어 있는 경우.
        KeyError: 프롬프트 키가 없거나 변수 치환에 실패한 경우.
    """
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("question 값은 비어 있을 수 없습니다.")

    system_prompt = prompt_manager.get_prompt(PLANNER_SYSTEM_PROMPT_KEY)
    user_prompt = prompt_manager.render_prompt(PLANNER_USER_PROMPT_KEY, {"question": clean_question})
    return system_prompt, user_prompt

