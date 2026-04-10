# 이 파일은 langgraph 패키지가 없는 환경에서도 그래프 흐름 테스트가 가능하도록 만든 대체 구현이다.
# 인터페이스는 StateGraph/START/END 핵심 메서드만 최소 범위로 호환한다.
# 운영에서는 실제 langgraph를 우선 사용하고, 이 모듈은 테스트/개발 안전망으로 동작한다.
# 노드 실행 순서와 조건 분기 동작을 단순화해 가독성과 유지보수성을 우선한다.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

START = "__start__"
END = "__end__"

State = dict[str, Any]
NodeFn = Callable[[State], dict[str, Any] | None]
RouteFn = Callable[[State], str]


@dataclass
class _ConditionalEdge:
    """조건부 라우팅 정보를 저장한다."""

    route_fn: RouteFn
    path_map: dict[str, str] | None


class CompiledFallbackGraph:
    """fallback 그래프 실행기."""

    def __init__(
        self,
        nodes: dict[str, NodeFn],
        edges: dict[str, list[str]],
        conditional_edges: dict[str, _ConditionalEdge],
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._conditional_edges = conditional_edges

    def invoke(self, state: State) -> State:
        """
        그래프를 시작 노드부터 끝 노드까지 실행한다.

        Args:
            state: 초기 상태 dict.

        Returns:
            State: 실행 후 최종 상태 dict.
        """
        current = self._next_node(START, state)
        while current != END:
            node_fn = self._nodes[current]
            updates = node_fn(state) or {}
            state.update(updates)
            current = self._next_node(current, state)
        return state

    def _next_node(self, current: str, state: State) -> str:
        """현재 노드 다음에 실행할 노드를 결정한다."""
        conditional = self._conditional_edges.get(current)
        if conditional is not None:
            route_key = conditional.route_fn(state)
            if conditional.path_map is None:
                return route_key
            if route_key not in conditional.path_map:
                raise ValueError(f"조건 분기 키가 path_map에 없습니다: {route_key}")
            return conditional.path_map[route_key]

        next_nodes = self._edges.get(current, [])
        if not next_nodes:
            raise ValueError(f"다음 노드가 정의되지 않았습니다: {current}")
        if len(next_nodes) > 1:
            raise ValueError(f"fallback 그래프는 단일 다음 노드만 지원합니다: {current} -> {next_nodes}")
        return next_nodes[0]


class StateGraph:
    """langgraph.graph.StateGraph 최소 호환 클래스."""

    def __init__(self, state_type: type[Any]) -> None:
        self._state_type = state_type
        self._nodes: dict[str, NodeFn] = {}
        self._edges: dict[str, list[str]] = {}
        self._conditional_edges: dict[str, _ConditionalEdge] = {}

    def add_node(self, name: str, node_fn: NodeFn) -> None:
        """노드를 추가한다."""
        self._nodes[name] = node_fn

    def add_edge(self, source: str, target: str) -> None:
        """단순 단방향 엣지를 추가한다."""
        self._edges.setdefault(source, []).append(target)

    def add_conditional_edges(
        self,
        source: str,
        route_fn: RouteFn,
        path_map: dict[str, str] | None = None,
    ) -> None:
        """조건부 엣지를 추가한다."""
        self._conditional_edges[source] = _ConditionalEdge(route_fn=route_fn, path_map=path_map)

    def compile(self) -> CompiledFallbackGraph:
        """실행 가능한 그래프 객체를 생성한다."""
        return CompiledFallbackGraph(
            nodes=self._nodes,
            edges=self._edges,
            conditional_edges=self._conditional_edges,
        )

