# 리팩터링 분석 문서

## 1) 현재 구조 요약

### 루트 구조
- `Planner/`: 사용자 질문을 `query_type + steps` 형태 JSON으로 계획화하는 계층
- `Root_Ingest/`: 문서 적재 파이프라인(로딩/파싱/청킹/임베딩/Chroma 저장)
- `Root_Stream/`: 질문 기반 SQL 생성, SQL 검증/실행, API/CLI 진입점
- `tests/`: 현재는 `Root_Stream` 중심의 `unittest` 테스트 세트

### Planner 역할
- `PlannerService`가 `Root_Stream`의 `config/prompt/llm` 유틸을 재사용
- `planner_prompt.py`로 Planner 전용 프롬프트 생성
- `plan_validator.py`로 JSON 구조 및 단계 의존성 검증
- 결과는 `PlannerPlan` dataclass로 반환

### Root_Ingest 역할
- `ingest_pipeline.py`가 전체 ingest 흐름을 순차 실행
  - `document_loader` → `parser_service` → `chunk_service` → `embedding_service` → `vector_store_service`
- `config.yaml/config.rag.yaml`로 ingest 대상과 collection 분리
- Notebook은 단계별 실험용으로 구성

### Root_Stream 역할
- `StreamOrchestrator`가 `mode(natural/prompt/rag_prompt)` 분기 후 mode 함수 호출
- `services/query_service.py`가 API/CLI 공용 SQL 생성 진입점
- `services/sql/*`에서 SQL Guard 및 MSSQL 실행 통합
- `services/e2e/planner_flow_runner.py`에 Planner→DB→RAG→최종답변 흐름이 별도로 존재
- `server/*`는 FastAPI 진입점

### 연결 관계
- `prompts`는 `PromptManager`를 통해 mode/Planner에서 공통 사용
- `services`는 LLM/RAG/SQL/DB 실행 책임
- `orchestrator`는 mode 분기와 호출 순서 책임
- `server`는 `query_service`를 호출
- `notebooks`는 서비스 함수를 직접 호출하며 실험

### 기존 테스트 범위
- `mode 해석`, `PromptManager`, `config loader`, `SqlGuard` 중심 단위 테스트
- Planner 쪽에는 실제 LLM 호출 기반 라이브 테스트 존재
- Graph 단위/통합/E2E(모의 객체 기반) 테스트는 부재

### LangGraph 전환 시 유지할 핵심 진입점
- CLI: `python -m Root_Stream.main`
- API: `Root_Stream.server.api_app`
- Planner 서비스: `Planner.planner_service.PlannerService`
- Ingest 파이프라인: `Root_Ingest.ingest.ingest_pipeline.run_ingest_pipeline`
- Notebook 실험: 기존 notebook에서 호출하던 서비스 함수

---

## 2) 문제점
- 오케스트레이션이 `StreamOrchestrator`와 `planner_flow_runner`에 분산됨
- 모드 분기/서비스 조합/후처리 로직이 중복됨
- 테스트가 핵심 흐름 단위로 분해되어 있지 않음(노드/라우팅 테스트 부재)
- 공통 유틸(logger/config/path)이 Root_Ingest/Root_Stream에 중복
- API/CLI/Notebook이 동일 실행 그래프를 공유하지 않음

---

## 3) 개선 방향
- `db_to_llm` 패키지에 역할 중심 구조를 추가하고 기존 코드를 재사용
- LangGraph 기반 상태(State) + 노드(Node) + 조건부 라우팅(Edge)로 실행 흐름 단일화
- 노드는 오케스트레이션만 수행, 실제 호출은 서비스 계층 위임
- 기존 진입점(CLI/API/E2E)에는 호환 래퍼를 두어 import 경로 파손 최소화
- 테스트를 `unit/integration/e2e`로 분리하고 모의 객체 기반으로 외부 의존성 제거

---

## 4) 유지 / 제거 / 이동

### 유지
- `Planner`의 모델/검증/서비스 로직
- `Root_Ingest` 파이프라인 및 parser/chunk/embed/vector 서비스
- `Root_Stream`의 LLM/RAG/SQL/DB 서비스 구현
- SQL Guard 중심 검증 원칙

### 제거(직접 제거보다 역할 축소)
- `StreamOrchestrator` 중심 mode 분기 책임
- `planner_flow_runner` 내부의 단일 파일 대형 흐름 조합 책임

### 이동/재배치
- 오케스트레이션 책임을 `db_to_llm.stream.graph`로 이동
- 공통 logger/config/state/type을 `db_to_llm.common`으로 이동
- 기존 엔트리포인트는 새 graph runner 호출용 thin wrapper로 정리

---

## 5) 최종 목표 구조

```text
DB_to_LLM/
  db_to_llm/
    common/
      config/
      logging/
      types/
    planner/
      services/
    ingest/
      pipelines/
    stream/
      graph/
      nodes/
      services/
      api/
      cli/
  tests/
    unit/
    integration/
    e2e/
    fixtures/
  docs/
    refactor_analysis.md
    langgraph_workflow.md
  Planner/          # 호환 유지(기존 코드)
  Root_Ingest/      # 호환 유지(기존 코드)
  Root_Stream/      # 호환 유지(기존 코드)
```

---

## 6) 설계 결정 근거
- `Planner/Root_Ingest/Root_Stream`를 즉시 제거하지 않고 호환 유지
  - 이유: 기존 import/Notebook/실행 스크립트 파손 방지
- 핵심 실행 흐름만 먼저 `db_to_llm.stream.graph`로 수렴
  - 이유: 가장 큰 중복(오케스트레이션)을 우선 제거
- 서비스 구현은 최대한 재사용하고 래퍼로 감쌈
  - 이유: 기능 회귀 위험과 리팩터링 비용 최소화

---

## 7) 파일 이동/재배치 내역

실제 파일 “물리 이동” 대신, 기존 파일을 보존하면서 신규 패키지로 책임을 재배치했다.

- `Root_Stream/main.py`
  - 기존: orchestrator 직접 호출
  - 변경: `db_to_llm.stream.graph.runner` 호출
- `Root_Stream/services/query_service.py`
  - 기존: orchestrator mode 분기 직접 호출
  - 변경: graph runner 기반 호환 래퍼
- 신규 오케스트레이션 계층
  - `db_to_llm/stream/graph/*`
  - `db_to_llm/stream/nodes/*`
  - `db_to_llm/stream/services/*`
- 공통 계층
  - `db_to_llm/common/config/runtime_config.py`
  - `db_to_llm/common/logging/logger.py`

---

## 8) 추후 개선 포인트
- `Planner`/`Root_Stream`/`Root_Ingest`의 공통 유틸(logger/config/path) 완전 단일화
- `services/e2e/planner_flow_runner.py`의 잔여 보조 로직을 신규 서비스 계층으로 점진 이관
- Notebook(`*.ipynb`)을 단계적으로 `db_to_llm.stream.graph.runner` 호출 형태로 정리
- API 응답 스키마에 `errors/debug_trace`를 선택적으로 노출하는 디버그 모드 추가
- 실제 DB/LLM 연결 환경을 위한 스모크 테스트 파이프라인(CI) 보강
