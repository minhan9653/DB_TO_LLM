# 이 파일은 PlannerService와 관련 모델의 단위 테스트를 정의한다.
# PlannerJsonParseError, PlanValidationError, validate_plan_payload(),
# PlannerPlan.from_dict(), PlannerService.plan_question()을 검증한다.
# Mock LLM 클라이언트를 사용해 실제 LLM 연결 없이 테스트한다.

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.db_to_llm.stream.planner.models import (
    VALID_QUERY_TYPES,
    PlannerPlan,
    PlannerStep,
)
from src.db_to_llm.stream.planner.plan_validator import (
    PlanValidationError,
    validate_plan_payload,
)
from src.db_to_llm.stream.planner.planner_service import (
    PlannerJsonParseError,
    PlannerService,
)


# ---------------------------------------------------------------------------
# 샘플 plan dict
# ---------------------------------------------------------------------------

VALID_PLAN_DICT = {
    "is_composite": False,
    "query_type": "DB_ONLY",
    "steps": [{"step": 1, "type": "db", "goal": "매출 데이터 조회", "depends_on": []}],
}

COMPOSITE_PLAN_DICT = {
    "is_composite": True,
    "query_type": "DB_THEN_RAG",
    "steps": [
        {"step": 1, "type": "db", "goal": "오류 코드 조회", "depends_on": []},
        {"step": 2, "type": "rag", "goal": "오류 문서 검색", "depends_on": [1]},
    ],
}


# ---------------------------------------------------------------------------
# PlannerPlan / PlannerStep 모델 테스트
# ---------------------------------------------------------------------------

class TestPlannerPlanModel:
    """PlannerPlan과 PlannerStep의 직렬화/역직렬화를 테스트한다."""

    def test_from_dict_db_only(self) -> None:
        """DB_ONLY plan을 dict에서 올바르게 생성한다."""
        plan = PlannerPlan.from_dict(VALID_PLAN_DICT)
        assert plan.query_type == "DB_ONLY"
        assert plan.is_composite is False
        assert len(plan.steps) == 1
        assert plan.steps[0].step == 1
        assert plan.steps[0].type == "db"

    def test_from_dict_composite(self) -> None:
        """DB_THEN_RAG 복합 plan을 올바르게 생성한다."""
        plan = PlannerPlan.from_dict(COMPOSITE_PLAN_DICT)
        assert plan.query_type == "DB_THEN_RAG"
        assert plan.is_composite is True
        assert len(plan.steps) == 2
        assert plan.steps[1].depends_on == [1]

    def test_to_dict_roundtrip(self) -> None:
        """to_dict()로 변환 후 from_dict()하면 동일한 값이 되어야 한다."""
        plan = PlannerPlan.from_dict(VALID_PLAN_DICT)
        restored = PlannerPlan.from_dict(plan.to_dict())
        assert restored.query_type == plan.query_type
        assert restored.is_composite == plan.is_composite
        assert len(restored.steps) == len(plan.steps)

    def test_all_valid_query_types(self) -> None:
        """VALID_QUERY_TYPES의 모든 값으로 PlannerPlan을 생성할 수 있어야 한다."""
        for query_type in VALID_QUERY_TYPES:
            plan_dict = {
                "is_composite": False,
                "query_type": query_type,
                "steps": [{"step": 1, "type": "db", "goal": "테스트", "depends_on": []}],
            }
            plan = PlannerPlan.from_dict(plan_dict)
            assert plan.query_type == query_type


# ---------------------------------------------------------------------------
# plan_validator 테스트
# ---------------------------------------------------------------------------

class TestPlanValidator:
    """validate_plan_payload() 함수를 테스트한다."""

    def test_valid_plan_passes(self) -> None:
        """올바른 plan dict는 예외 없이 통과해야 한다."""
        validate_plan_payload(VALID_PLAN_DICT)  # 예외가 발생하지 않으면 통과

    def test_missing_required_field_raises(self) -> None:
        """필수 필드가 없으면 PlanValidationError를 발생시켜야 한다."""
        for field_name in ["is_composite", "query_type", "steps"]:
            incomplete = {k: v for k, v in VALID_PLAN_DICT.items() if k != field_name}
            with pytest.raises(PlanValidationError, match=field_name):
                validate_plan_payload(incomplete)

    def test_invalid_query_type_raises(self) -> None:
        """허용되지 않는 query_type은 PlanValidationError를 발생시켜야 한다."""
        bad_plan = {**VALID_PLAN_DICT, "query_type": "INVALID_TYPE"}
        with pytest.raises(PlanValidationError, match="query_type"):
            validate_plan_payload(bad_plan)

    def test_empty_steps_raises(self) -> None:
        """빈 steps는 PlanValidationError를 발생시켜야 한다."""
        bad_plan = {**VALID_PLAN_DICT, "steps": []}
        with pytest.raises(PlanValidationError, match="steps"):
            validate_plan_payload(bad_plan)

    def test_non_sequential_steps_raises(self) -> None:
        """step 번호가 1부터 순차적이지 않으면 PlanValidationError를 발생시켜야 한다."""
        bad_plan = {
            **VALID_PLAN_DICT,
            "steps": [
                {"step": 2, "type": "db", "goal": "건너뜀", "depends_on": []},
            ],
        }
        with pytest.raises(PlanValidationError):
            validate_plan_payload(bad_plan)

    def test_invalid_depends_on_reference_raises(self) -> None:
        """depends_on이 존재하지 않는 step을 참조하면 PlanValidationError를 발생시켜야 한다."""
        bad_plan = {
            **COMPOSITE_PLAN_DICT,
            "steps": [
                {"step": 1, "type": "db", "goal": "조회", "depends_on": []},
                {"step": 2, "type": "rag", "goal": "검색", "depends_on": [99]},  # 99는 없음
            ],
        }
        with pytest.raises(PlanValidationError):
            validate_plan_payload(bad_plan)


# ---------------------------------------------------------------------------
# PlannerService 테스트
# ---------------------------------------------------------------------------

class TestPlannerService:
    """PlannerService.plan_question()을 Mock LLM으로 테스트한다."""

    def _make_service(self, llm_response: str) -> PlannerService:
        """지정된 응답을 반환하는 PlannerService를 생성한다."""
        mock_llm = MagicMock()
        mock_llm.provider_name = "mock"
        mock_llm.generate.return_value = llm_response

        mock_pm = MagicMock()
        mock_pm.render.return_value = "렌더된 프롬프트"

        return PlannerService(llm_client=mock_llm, prompt_manager=mock_pm)

    def test_success_returns_plan(self) -> None:
        """LLM이 올바른 JSON을 반환하면 PlannerPlan을 반환해야 한다."""
        response_json = json.dumps(VALID_PLAN_DICT, ensure_ascii=False)
        service = self._make_service(response_json)
        plan = service.plan_question("지난달 매출 알려줘")
        assert plan.query_type == "DB_ONLY"
        assert len(plan.steps) == 1

    def test_json_in_markdown_code_block(self) -> None:
        """마크다운 코드블록 안의 JSON도 파싱할 수 있어야 한다."""
        response = f"```json\n{json.dumps(VALID_PLAN_DICT, ensure_ascii=False)}\n```"
        service = self._make_service(response)
        plan = service.plan_question("매출 조회해줘")
        assert plan.query_type == "DB_ONLY"

    def test_fallback_on_invalid_json(self) -> None:
        """JSON 파싱 실패 시 GENERAL 타입으로 폴백해야 한다."""
        service = self._make_service("완전히 망가진 텍스트입니다. JSON이 아닙니다.")
        plan = service.plan_question("아무 질문")
        assert plan.query_type == "GENERAL"

    def test_fallback_on_invalid_plan(self) -> None:
        """JSON은 파싱됐지만 검증 실패 시 GENERAL 타입으로 폴백해야 한다."""
        bad_plan = {"is_composite": False, "query_type": "UNKNOWN_TYPE", "steps": []}
        service = self._make_service(json.dumps(bad_plan))
        plan = service.plan_question("아무 질문")
        assert plan.query_type == "GENERAL"
