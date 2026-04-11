# 이 파일은 사용자 질문을 받아 LLM으로 실행 계획(PlannerPlan)을 생성하는 핵심 서비스이다.
# planner_prompt.py로 프롬프트를 만들고 LLM을 호출한 뒤 JSON을 파싱해 검증한다.
# planner_node.py가 이 서비스를 호출해 그래프 state에 planner_result를 저장한다.
# LLM 응답 파싱 실패 시 PlannerJsonParseError, 검증 실패 시 PlanValidationError를 발생시킨다.

from __future__ import annotations

import json
import re
from typing import Any

from src.db_to_llm.shared.llm.base_llm import BaseLLMClient
from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.planner.models import PlannerPlan
from src.db_to_llm.stream.planner.plan_validator import PlanValidationError, validate_plan_payload
from src.db_to_llm.stream.planner.planner_prompt import build_planner_prompts
from src.db_to_llm.stream.prompts.prompt_manager import PromptManager

logger = get_logger(__name__)


class PlannerJsonParseError(ValueError):
    """Planner LLM 응답을 JSON으로 파싱하지 못한 경우 발생하는 예외."""
    pass


class PlannerService:
    """사용자 질문을 LLM으로 분석해 PlannerPlan을 생성하는 서비스."""

    def __init__(self, llm_client: BaseLLMClient, prompt_manager: PromptManager) -> None:
        """
        PlannerService를 초기화한다.

        Args:
            llm_client: LLM 호출에 사용할 클라이언트. (Ollama/OpenAI)
            prompt_manager: 프롬프트 조회용 PromptManager 인스턴스.
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    def plan_question(self, question: str) -> PlannerPlan:
        """
        질문을 분석해 실행 계획(PlannerPlan)을 생성한다.

        Args:
            question: 사용자가 입력한 질문.

        Returns:
            PlannerPlan: LLM이 생성한 검증 완료된 실행 계획.

        Raises:
            PlannerJsonParseError: LLM 응답을 JSON으로 파싱하지 못한 경우.
            PlanValidationError: 계획 내용이 검증 규칙에 맞지 않는 경우.
        """
        logger.info("Planner 계획 생성 시작: question=%s", question[:50])

        # 1. 프롬프트 생성
        system_prompt, user_prompt = build_planner_prompts(
            question=question,
            prompt_manager=self.prompt_manager,
        )

        # 2. LLM 호출
        logger.info("Planner LLM 호출 시작")
        try:
            raw_response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
            )
        except Exception:
            logger.exception("Planner LLM 호출 실패")
            raise

        logger.info("Planner LLM 응답 수신: length=%d", len(raw_response))
        logger.debug("Planner 원본 응답: %s", raw_response[:200])

        # 3. JSON 파싱
        plan_data = self._parse_json_response(raw_response)

        # 4. 내용 검증
        try:
            validate_plan_payload(plan_data)
        except PlanValidationError:
            logger.exception("Planner 계획 검증 실패: plan_data=%s", plan_data)
            raise

        # 5. 모델로 변환
        plan = PlannerPlan.from_dict(plan_data)
        logger.info(
            "Planner 계획 생성 완료: query_type=%s, steps=%d",
            plan.query_type,
            len(plan.steps),
        )
        return plan

    def _parse_json_response(self, raw_response: str) -> dict[str, Any]:
        """
        LLM 응답 문자열에서 JSON 객체를 추출해 파싱한다.
        마크다운 코드블록이 있으면 벗겨내고 순수 JSON만 파싱한다.

        Args:
            raw_response: LLM이 반환한 원본 텍스트.

        Returns:
            dict: 파싱된 JSON dict.

        Raises:
            PlannerJsonParseError: JSON 파싱에 실패한 경우 발생한다.
        """
        # 마크다운 코드블록 제거: ```json ... ``` 또는 ``` ... ```
        cleaned = re.sub(r"```(?:json)?\s*\n?", "", raw_response, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "").strip()

        # JSON 객체 부분만 추출 ({...})
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if not json_match:
            raise PlannerJsonParseError(
                f"LLM 응답에서 JSON을 찾을 수 없습니다. 응답 앞부분: {raw_response[:100]}"
            )

        json_text = json_match.group(0)

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as error:
            raise PlannerJsonParseError(
                f"JSON 파싱 실패: {error}. 시도한 텍스트: {json_text[:200]}"
            ) from error
