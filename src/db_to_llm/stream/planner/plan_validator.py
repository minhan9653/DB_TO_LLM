# 이 파일은 Planner LLM이 반환한 JSON 계획을 검증하는 역할을 담당한다.
# 필수 필드, query_type 허용값, step 순서, depends_on 참조를 검증한다.
# PlannerService가 LLM 응답을 파싱한 직후 이 함수를 호출해 잘못된 계획을 차단한다.
# 검증 실패 시 명확한 오류 메시지와 함께 ValueError를 발생시킨다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.stream.planner.models import VALID_QUERY_TYPES


class PlanValidationError(ValueError):
    """Planner 계획 검증 실패를 나타내는 예외."""
    pass


def validate_plan_payload(plan_data: dict[str, Any]) -> None:
    """
    Planner LLM이 반환한 계획 dict를 검증한다.
    검증 통과 시 None을 반환하고, 실패 시 PlanValidationError를 발생시킨다.

    Args:
        plan_data: LLM 응답을 JSON 파싱한 dict.

    Raises:
        PlanValidationError: 필수 필드 누락, 잘못된 query_type, step 순서 오류,
                             depends_on 참조 오류가 있는 경우 발생한다.
    """
    # 필수 최상위 필드 확인
    required_fields = ["is_composite", "query_type", "steps"]
    for field_name in required_fields:
        if field_name not in plan_data:
            raise PlanValidationError(f"필수 필드가 없습니다: '{field_name}'")

    # query_type 허용값 확인
    query_type = str(plan_data.get("query_type", "")).upper()
    if query_type not in VALID_QUERY_TYPES:
        valid_list = ", ".join(sorted(VALID_QUERY_TYPES))
        raise PlanValidationError(
            f"허용되지 않는 query_type입니다: '{query_type}'. 허용값: {valid_list}"
        )

    # steps 형식 확인
    steps = plan_data.get("steps", [])
    if not isinstance(steps, list):
        raise PlanValidationError("steps는 list 형식이어야 합니다.")
    if len(steps) == 0:
        raise PlanValidationError("steps가 비어 있습니다. 최소 1개의 step이 필요합니다.")

    _validate_step_order_and_fields(steps)
    _validate_depends_on_references(steps)


def _validate_step_order_and_fields(steps: list[dict[str, Any]]) -> None:
    """step 번호가 1부터 순차적으로 있는지, 필수 필드가 있는지 확인한다."""
    for idx, step in enumerate(steps):
        expected_step_number = idx + 1
        actual_step_number = step.get("step")

        if actual_step_number != expected_step_number:
            raise PlanValidationError(
                f"step 번호 오류: {idx}번째 step의 번호가 {actual_step_number}이어야 하는데 "
                f"{expected_step_number}을 기대했습니다."
            )

        step_type = step.get("type", "")
        if step_type not in {"db", "rag", "general"}:
            raise PlanValidationError(
                f"step {expected_step_number}: type은 'db', 'rag', 'general' 중 하나여야 합니다. "
                f"받은 값: '{step_type}'"
            )

        if not step.get("goal"):
            raise PlanValidationError(f"step {expected_step_number}: goal 필드가 비어 있습니다.")


def _validate_depends_on_references(steps: list[dict[str, Any]]) -> None:
    """depends_on이 존재하고 이전 step만 참조하는지 확인한다."""
    for step in steps:
        current_step_number = step.get("step", 0)
        depends_on = step.get("depends_on", [])

        if not isinstance(depends_on, list):
            raise PlanValidationError(
                f"step {current_step_number}: depends_on은 list 형식이어야 합니다."
            )

        for referenced_step in depends_on:
            if not isinstance(referenced_step, int):
                raise PlanValidationError(
                    f"step {current_step_number}: depends_on 값은 정수 step 번호여야 합니다. "
                    f"받은 값: {referenced_step}"
                )
            if referenced_step >= current_step_number:
                raise PlanValidationError(
                    f"step {current_step_number}: depends_on은 이전 step 번호만 참조할 수 있습니다. "
                    f"참조된 step: {referenced_step}"
                )
