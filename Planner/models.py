# 이 파일은 Planner 단계의 입출력 데이터 구조를 dataclass로 정의한다.
# PlannerService는 LLM 원문 응답을 PlannerPlan 모델로 변환해 반환한다.
# plan_validator는 JSON 최소 검증을 담당하고, 이 모델은 구조화 표현만 담당한다.
# 디버그 스크립트/테스트/노트북이 동일 모델 타입을 재사용하도록 연결한다.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

QUERY_TYPES: tuple[str, ...] = (
    "DB_ONLY",
    "RAG_ONLY",
    "GENERAL",
    "DB_THEN_RAG",
    "DB_THEN_GENERAL",
    "RAG_THEN_GENERAL",
)

STEP_TYPES: tuple[str, ...] = ("db", "rag", "general")


@dataclass
class PlannerStep:
    """Planner 단계의 단일 실행 step 모델이다."""

    step: int
    type: str
    goal: str
    depends_on: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerStep":
        """
        JSON dict를 PlannerStep 모델로 변환한다.
        """
        return cls(
            step=int(payload["step"]),
            type=str(payload["type"]),
            goal=str(payload["goal"]),
            depends_on=[int(item) for item in payload.get("depends_on", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        """
        PlannerStep 모델을 JSON 직렬화 가능한 dict로 변환한다.
        """
        return asdict(self)


@dataclass
class PlannerPlan:
    """Planner 단계의 최종 실행 계획 모델이다."""

    is_composite: bool
    query_type: str
    steps: list[PlannerStep]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerPlan":
        """
        JSON dict를 PlannerPlan 모델로 변환한다.
        """
        steps = [PlannerStep.from_dict(step_payload) for step_payload in payload.get("steps", [])]
        return cls(
            is_composite=bool(payload["is_composite"]),
            query_type=str(payload["query_type"]),
            steps=steps,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        PlannerPlan 모델을 JSON 직렬화 가능한 dict로 변환한다.
        """
        payload = asdict(self)
        payload["steps"] = [step.to_dict() for step in self.steps]
        return payload


@dataclass
class PlannerRunResult:
    """Planner 실행 결과(원문 응답 + 파싱 모델)를 묶은 모델이다."""

    question: str
    raw_response: str
    plan: PlannerPlan

    def to_dict(self) -> dict[str, Any]:
        """
        PlannerRunResult 모델을 JSON 직렬화 가능한 dict로 변환한다.
        """
        return {
            "question": self.question,
            "raw_response": self.raw_response,
            "plan": self.plan.to_dict(),
        }

