# 이 파일은 Planner LLM 응답 JSON의 최소 형식 검증을 담당한다.
# PlannerService는 JSON 파싱 후 이 검증 함수를 반드시 호출한다.
# 검증 실패 시 명확한 오류 메시지를 제공해 디버깅 시간을 줄인다.
# 기존 Root_Stream 실행 흐름과 독립적으로 Planner 품질만 점검할 수 있게 한다.

from __future__ import annotations

from typing import Any

from Planner.models import QUERY_TYPES, STEP_TYPES


class PlanValidationError(ValueError):
    """Planner JSON 구조가 요구사항과 다를 때 발생하는 예외다."""


def validate_plan_payload(plan_payload: dict[str, Any]) -> None:
    """
    Planner JSON의 최소 필드/참조 규칙을 검증한다.

    Args:
        plan_payload: LLM 응답을 json.loads로 파싱한 dict 객체.

    Raises:
        PlanValidationError: 필수 필드 누락, 타입 오류, 참조 오류가 있을 때.
    """
    if not isinstance(plan_payload, dict):
        raise PlanValidationError("Planner 응답은 JSON object(dict)여야 합니다.")

    if "is_composite" not in plan_payload:
        raise PlanValidationError("필수 필드 누락: is_composite")
    if not isinstance(plan_payload["is_composite"], bool):
        raise PlanValidationError("is_composite는 bool 타입이어야 합니다.")

    query_type = plan_payload.get("query_type")
    if query_type is None:
        raise PlanValidationError("필수 필드 누락: query_type")
    if not isinstance(query_type, str) or not query_type.strip():
        raise PlanValidationError("query_type은 비어있지 않은 문자열이어야 합니다.")
    if query_type not in QUERY_TYPES:
        allowed_query_types = ", ".join(QUERY_TYPES)
        raise PlanValidationError(
            f"query_type 값이 허용 범위를 벗어났습니다: {query_type}. 허용값: {allowed_query_types}"
        )

    steps = plan_payload.get("steps")
    if not isinstance(steps, list) or not steps:
        raise PlanValidationError("steps는 비어있지 않은 list여야 합니다.")

    step_numbers = _validate_step_order_and_fields(steps)
    _validate_depends_on_references(steps, step_numbers)


def _validate_step_order_and_fields(steps: list[Any]) -> set[int]:
    """
    step 순서, 타입, 목표 텍스트 등 각 step 기본 규칙을 검증한다.
    """
    step_numbers: set[int] = set()
    allowed_step_types = ", ".join(STEP_TYPES)

    for expected_step_number, step_payload in enumerate(steps, start=1):
        if not isinstance(step_payload, dict):
            raise PlanValidationError(f"steps[{expected_step_number}]는 object(dict)여야 합니다.")

        step_number = step_payload.get("step")
        if step_number != expected_step_number:
            raise PlanValidationError(
                f"step 번호는 1부터 순서대로여야 합니다. 기대값={expected_step_number}, 실제값={step_number}"
            )

        step_type = step_payload.get("type")
        if step_type not in STEP_TYPES:
            raise PlanValidationError(
                f"step.type 허용값 오류: step={step_number}, type={step_type}, 허용값={allowed_step_types}"
            )

        goal = step_payload.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            raise PlanValidationError(f"goal은 비어있지 않은 문자열이어야 합니다. step={step_number}")

        depends_on = step_payload.get("depends_on")
        if not isinstance(depends_on, list):
            raise PlanValidationError(f"depends_on은 list여야 합니다. step={step_number}")

        step_numbers.add(expected_step_number)

    return step_numbers


def _validate_depends_on_references(steps: list[Any], step_numbers: set[int]) -> None:
    """
    depends_on이 존재하는 step 번호만 참조하는지 검증한다.
    """
    for step_payload in steps:
        step_number = int(step_payload["step"])
        depends_on = step_payload.get("depends_on", [])

        for dependency_step in depends_on:
            if not isinstance(dependency_step, int):
                raise PlanValidationError(
                    f"depends_on 값은 int여야 합니다. step={step_number}, value={dependency_step}"
                )
            if dependency_step not in step_numbers:
                raise PlanValidationError(
                    f"depends_on이 존재하지 않는 step을 참조합니다. step={step_number}, depends_on={dependency_step}"
                )
            if dependency_step >= step_number:
                raise PlanValidationError(
                    f"depends_on은 현재 step 이전 번호만 참조해야 합니다. step={step_number}, depends_on={dependency_step}"
                )

