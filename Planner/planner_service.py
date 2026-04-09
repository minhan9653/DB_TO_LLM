# 이 파일은 질문을 Planner JSON 실행 계획으로 변환하는 서비스 진입점을 담당한다.
# Root_Stream의 load_config, PromptManager, create_llm_client를 그대로 재사용한다.
# 새 LLM 클라이언트를 만들지 않고 기존 provider 설정/예외 흐름을 유지한다.
# 반환 범위는 JSON 파싱/검증까지이며 DB 실행, RAG 검색, SQL 생성은 포함하지 않는다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Planner.models import PlannerPlan, PlannerRunResult
from Planner.plan_validator import validate_plan_payload
from Planner.planner_prompt import build_planner_prompts
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.llm_factory import create_llm_client
from Root_Stream.utils.config_loader import load_config
from Root_Stream.utils.logger import get_logger, setup_logger
from Root_Stream.utils.path_utils import resolve_path

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "Root_Stream" / "config" / "config.yaml"


class PlannerJsonParseError(ValueError):
    """Planner LLM 응답이 JSON으로 파싱되지 않을 때 발생하는 예외다."""


class PlannerService:
    """질문을 Planner JSON 실행 계획으로 변환하는 서비스 클래스다."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """
        PlannerService 실행에 필요한 설정, 로거, 프롬프트, LLM 클라이언트를 초기화한다.
        """
        self.config_path = Path(config_path or DEFAULT_CONFIG_PATH).resolve()
        self.config = load_config(self.config_path)
        self.project_root = self._resolve_project_root()
        self._configure_logging()
        self.prompt_manager = self._build_prompt_manager()
        self.llm_client = create_llm_client(self.config)

        logger.info(
            "PlannerService 초기화 완료: config=%s, llm_provider=%s",
            self.config_path,
            self.config.get("llm_provider"),
        )

    def plan_question(self, question: str, *, temperature: float = 0.0) -> PlannerRunResult:
        """
        질문을 입력받아 Planner JSON 계획을 생성하고 검증한다.

        Args:
            question: 실행 계획을 만들 사용자 질문.
            temperature: LLM 생성 temperature (기본값 0.0).

        Returns:
            PlannerRunResult: raw_response와 구조화된 PlannerPlan을 포함한 결과.

        Raises:
            ValueError: 질문이 비어 있거나 JSON 구조가 잘못된 경우.
            PlannerJsonParseError: JSON 파싱 실패 시.
            PlanValidationError: JSON 형식 검증 실패 시.
            Exception: LLM 호출/프롬프트 로딩 실패 시 하위 예외가 전파될 수 있음.
        """
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("question 값은 비어 있을 수 없습니다.")

        logger.info("Planner 실행 시작: question_length=%d", len(clean_question))
        try:
            system_prompt, user_prompt = build_planner_prompts(
                prompt_manager=self.prompt_manager,
                question=clean_question,
            )
            raw_response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
            parsed_payload = self._parse_json_response(raw_response)
            validate_plan_payload(parsed_payload)
            planner_plan = PlannerPlan.from_dict(parsed_payload)
        except Exception:
            logger.exception("Planner 실행 실패")
            raise

        logger.info(
            "Planner 실행 완료: query_type=%s, step_count=%d",
            planner_plan.query_type,
            len(planner_plan.steps),
        )
        return PlannerRunResult(
            question=clean_question,
            raw_response=raw_response,
            plan=planner_plan,
        )

    def _resolve_project_root(self) -> Path:
        """
        config의 paths.project_root를 Root_Stream 기준으로 해석한다.
        """
        stream_root = self.config_path.parent.parent
        return resolve_path(self.config.get("paths", {}).get("project_root", "."), stream_root)

    def _configure_logging(self) -> None:
        """
        Root_Stream 로깅 설정 규칙을 그대로 재사용해 Planner 로그를 초기화한다.
        """
        log_level = str(self.config.get("logging", {}).get("level", "INFO"))
        log_file_value = self.config.get("paths", {}).get("log_file")
        log_file_path = resolve_path(log_file_value, self.project_root) if log_file_value else None
        setup_logger(log_level=log_level, log_file_path=log_file_path)

    def _build_prompt_manager(self) -> PromptManager:
        """
        config의 paths.prompt_file을 해석해 PromptManager를 생성한다.
        """
        prompt_file_value = self.config.get("paths", {}).get("prompt_file")
        if not prompt_file_value:
            raise ValueError("config.paths.prompt_file 값이 필요합니다.")

        prompt_file_path = resolve_path(prompt_file_value, self.project_root)
        return PromptManager(prompt_file_path=prompt_file_path)

    @staticmethod
    def _parse_json_response(raw_response: str) -> dict[str, Any]:
        """
        LLM 문자열 응답을 JSON dict로 파싱한다.
        """
        normalized = raw_response.strip()
        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as error:
            snippet = normalized.replace("\n", " ")[:300]
            raise PlannerJsonParseError(
                "Planner 응답 JSON 파싱 실패: "
                f"message={error.msg}, line={error.lineno}, col={error.colno}, raw_snippet={snippet!r}"
            ) from error

        if not isinstance(payload, dict):
            raise PlannerJsonParseError("Planner 응답 JSON은 최상위 object(dict)여야 합니다.")

        return payload


def create_planner_service(config_path: str | Path | None = None) -> PlannerService:
    """
    외부 호출부에서 PlannerService를 간단히 생성하기 위한 팩토리 함수다.
    """
    return PlannerService(config_path=config_path)

