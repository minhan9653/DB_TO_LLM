# 이 파일은 사용자 질문을 받아 Planner LLM을 호출하고 실행 계획을 만드는 노드이다.
# PlannerService를 통해 LLM에 질문하고 결과를 state에 저장한다.
# 실패 시 기본값(GENERAL)으로 graceful degradation 처리해 그래프가 계속 진행된다.
# planner_result, query_type, planner_steps가 이 노드의 주요 출력이다.

from __future__ import annotations

from src.db_to_llm.shared.llm.llm_factory import create_llm_client
from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.planner.planner_service import PlannerService
from src.db_to_llm.stream.services.prompt_service import get_prompt_manager

logger = get_logger(__name__)

# Planner 실패 시 사용할 기본 plan
_DEFAULT_PLAN = {
    "is_composite": False,
    "query_type": "GENERAL",
    "steps": [{"step": 1, "type": "general", "goal": "일반 답변 생성", "depends_on": []}],
}


def planner_node(state: GraphState) -> GraphState:
    """
    사용자 질문을 PlannerService로 분석해 실행 계획을 state에 저장한다.

    입력 state 키: question
    출력 state 키: planner_result, query_type, planner_steps, trace_logs, errors

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: planner_result, query_type, planner_steps가 추가된 상태.
    """
    question = state.get("question", "")
    logger.info("planner_node 시작: question=%s", question[:50])

    config = get_config(state)
    llm_client = create_llm_client(config)
    prompt_manager = get_prompt_manager(config)

    planner_service = PlannerService(
        llm_client=llm_client,
        prompt_manager=prompt_manager,
    )

    try:
        plan = planner_service.plan_question(question=question)
        plan_dict = plan.to_dict()

        logger.info(
            "planner_node 완료: query_type=%s, steps=%d",
            plan.query_type,
            len(plan.steps),
        )

        return {
            **state,
            "planner_result": plan_dict,
            "query_type": plan.query_type,
            "planner_steps": [step.to_dict() for step in plan.steps],
            "trace_logs": append_trace(state, f"planner_node: query_type={plan.query_type}"),
        }

    except Exception as error:
        logger.error("planner_node 실패, 기본값(GENERAL)으로 대체: %s", error)
        return {
            **state,
            "planner_result": _DEFAULT_PLAN,
            "query_type": "GENERAL",
            "planner_steps": _DEFAULT_PLAN["steps"],
            "errors": append_error(state, f"planner_node 실패: {error}"),
            "trace_logs": append_trace(state, "planner_node: 실패, GENERAL로 대체"),
        }
