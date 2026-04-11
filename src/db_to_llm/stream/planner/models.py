# 이 파일은 Planner가 반환하는 계획의 데이터 모델을 정의한다.
# PlannerStep은 단일 실행 단계, PlannerPlan은 전체 계획을 담는다.
# graph state에 저장되어 router가 이 값을 보고 다음 노드를 결정한다.
# from_dict()/to_dict()로 JSON 직렬화와 상태 전달을 지원한다.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# query_type 허용 값 목록
VALID_QUERY_TYPES = {
    "DB_ONLY",
    "RAG_ONLY",
    "GENERAL",
    "DB_THEN_RAG",
    "DB_THEN_GENERAL",
    "RAG_THEN_GENERAL",
}


@dataclass
class PlannerStep:
    """Planner가 생성한 단일 실행 단계를 나타낸다."""

    step: int                       # step 번호 (1부터 시작)
    type: str                       # "db" | "rag" | "general"
    goal: str                       # 이 단계에서 달성할 목표
    depends_on: list[int] = field(default_factory=list)  # 선행 step 번호 목록

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannerStep":
        """dict를 PlannerStep으로 변환한다."""
        return cls(
            step=int(data.get("step", 1)),
            type=str(data.get("type", "general")),
            goal=str(data.get("goal", "")),
            depends_on=list(data.get("depends_on", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        """PlannerStep을 dict로 변환한다."""
        return asdict(self)


@dataclass
class PlannerPlan:
    """Planner가 생성한 전체 실행 계획을 나타낸다."""

    is_composite: bool              # 복합 질의 여부
    query_type: str                 # VALID_QUERY_TYPES 중 하나
    steps: list[PlannerStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannerPlan":
        """
        dict를 PlannerPlan으로 변환한다.

        Args:
            data: Planner LLM이 반환한 JSON을 파싱한 dict.

        Returns:
            PlannerPlan: 변환된 계획 인스턴스.
        """
        steps = [
            PlannerStep.from_dict(step_data)
            for step_data in data.get("steps", [])
        ]
        return cls(
            is_composite=bool(data.get("is_composite", False)),
            query_type=str(data.get("query_type", "GENERAL")).upper(),
            steps=steps,
        )

    def to_dict(self) -> dict[str, Any]:
        """PlannerPlan을 dict로 변환한다."""
        return {
            "is_composite": self.is_composite,
            "query_type": self.query_type,
            "steps": [step.to_dict() for step in self.steps],
        }
