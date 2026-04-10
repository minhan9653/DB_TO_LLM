# 이 파일은 기존 PlannerService를 LangGraph 노드에서 재사용하기 위한 어댑터다.
# 기존 로직을 그대로 호출하고 결과를 dict 형태로 표준화해 반환한다.
# Graph 노드에서는 Planner 구현 세부사항을 몰라도 되도록 의존성을 분리한다.
# 테스트에서는 이 함수를 모킹해 외부 LLM 의존 없이 흐름을 검증할 수 있다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Planner.planner_service import PlannerService
from db_to_llm.common.logging.logger import get_logger

logger = get_logger(__name__)


def run_planner(question: str, config_path: Path) -> dict[str, Any]:
    """
    기존 PlannerService를 호출해 질문 계획 결과를 표준 형태로 반환한다.

    Args:
        question: 사용자 질문.
        config_path: Stream config 경로.

    Returns:
        dict[str, Any]: planner_raw/planner_result/query_type/reasoning_summary 포함 결과.
    """
    planner_service = PlannerService(config_path=config_path)
    planner_run = planner_service.plan_question(question)
    planner_result = planner_run.plan.to_dict()
    reasoning_summary = _extract_reasoning_summary(planner_run.raw_response)

    logger.info("Planner 완료: query_type=%s", planner_run.plan.query_type)
    return {
        "planner_raw": planner_run.raw_response,
        "planner_result": planner_result,
        "query_type": planner_run.plan.query_type,
        "reasoning_summary": reasoning_summary,
    }


def _extract_reasoning_summary(raw_response: str) -> str | None:
    """
    Planner raw JSON에서 reasoning_summary를 안전하게 추출한다.

    Args:
        raw_response: Planner LLM raw 응답 문자열.

    Returns:
        str | None: reasoning_summary 문자열 또는 None.
    """
    try:
        payload = json.loads(raw_response)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("reasoning_summary")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None

