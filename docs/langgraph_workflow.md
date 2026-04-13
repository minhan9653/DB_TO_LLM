# LangGraph 워크플로 문서

## 1) 개요
- 실행 핵심은 `db_to_llm.stream.graph`에 모은 LangGraph 기반 오케스트레이션이다.
- CLI/API/Notebook은 동일한 `run_stream_graph()`를 호출한다.
- 노드는 오케스트레이션만 담당하고 실제 처리(LLM/RAG/SQL/DB)는 서비스 계층으로 위임한다.

## 2) 상태(State) 구조
주요 상태 필드(`StreamGraphState`):
- `question`, `normalized_question`
- `mode`, `execute_sql`, `config_path`
- `planner_result`, `query_type`, `planner_steps`, `reasoning_summary`
- `route_type`
- `retrieved_context`
- `generated_sql`, `sql_validation_result`, `validated_sql`
- `execution_result`, `db_rows`, `db_summary`
- `final_answer`
- `errors`, `debug_trace`

## 3) 노드 설명
- `load_runtime_config_node`
  - config/logger/prompt_manager/llm_client 초기화
- `planner_node`
  - Planner 실행, `query_type` 및 steps 반영
- `natural_llm_node`
  - 기본 프롬프트 기반 SQL 초안 생성
- `prompt_llm_node`
  - 템플릿 프롬프트 기반 SQL 초안 생성
- `rag_retrieve_node`
  - Chroma RAG 검색 수행
- `rag_prompt_llm_node`
  - RAG 컨텍스트 포함 프롬프트로 SQL 생성
- `sql_validation_node`
  - SQL Guard 검증
- `db_execute_node`
  - `execute_sql=True`이고 SQL 검증 성공 시 DB 실행
- `result_summary_node`
  - DB 실행 결과 요약
- `final_response_node`
  - Planner/SQL/DB/RAG/에러를 종합한 최종 응답 생성

## 4) 엣지/라우팅
기본 흐름:

`START -> load_runtime_config_node -> planner_node -> (분기) -> ... -> sql_validation_node -> (분기) -> ... -> final_response_node -> END`

분기 규칙:
- `route_by_plan`
  - 명시 mode 우선 (`natural/prompt/rag_prompt`)
  - mode가 `auto`면 Planner `query_type`로 분기
- `route_after_sql_validation`
  - `execute_sql=True` + `is_valid=True` + `validated_sql` 존재 시 `db_execute_node`
  - 그 외는 `final_response_node`

## 5) 실행 예시

CLI:
```bash
python -m Root_Stream.main --question "최근 24시간 장비별 에러 건수 알려줘"
python -m Root_Stream.main --execute-sql --question "최근 24시간 장비별 에러 건수 알려줘"
```

API:
```bash
uvicorn Root_Stream.server.api_app:app --host 127.0.0.1 --port 8000 --reload
```

Python 코드:
```python
from db_to_llm.stream.graph.runner import run_stream_graph

result = run_stream_graph(
    question="최근 24시간 장비별 에러 건수 알려줘",
    mode="auto",
    execute_sql=False,
)
print(result.payload["generated_sql"])
```

## 6) 테스트 전략
- `tests/unit`
  - Planner payload 파싱/검증
  - 라우팅 함수
  - 프롬프트 조합
  - SQL validator 서비스
  - runtime config/상태 헬퍼
- `tests/integration`
  - 그래프 노드 조합 테스트
  - natural/prompt/rag 분기
  - `execute_sql=True/False` 분기
  - LLM/DB/RAG 모킹
- `tests/e2e`
  - 질문 1개 기준 전체 흐름(Planner→Route→SQL→Validate→Execute→Final) 검증
  - 외부 시스템 없이 fixture/mock 기반 재현
