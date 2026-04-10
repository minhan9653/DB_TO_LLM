# DB_TO_LLM

## 프로젝트 개요
- 본 프로젝트는 자연어 질문을 Planner 기반으로 분해하고, LangGraph 노드 오케스트레이션으로 SQL/RAG/DB 실행 흐름을 제어합니다.
- 기존 `Planner`, `Root_Ingest`, `Root_Stream` 기능을 유지하면서 `db_to_llm` 패키지에 역할 중심 구조를 추가했습니다.
- SQL은 반드시 검증(`SqlGuard`) 단계를 거친 뒤에만 실행됩니다.

## 핵심 구조
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
  Planner/
  Root_Ingest/
  Root_Stream/
  tests/
    unit/
    integration/
    e2e/
    fixtures/
  docs/
    refactor_analysis.md
    langgraph_workflow.md
```

## LangGraph 기반 실행 흐름
기본 그래프:

`START -> load_runtime_config -> planner -> route -> (natural|prompt|rag) -> sql_validation -> (optional db_execute -> result_summary) -> final_response -> END`

- 조건부 분기 기준
  - Planner `query_type`
  - 명시 mode(`natural`, `prompt`, `rag_prompt`)
  - `execute_sql` 여부

상세는 [docs/langgraph_workflow.md](docs/langgraph_workflow.md) 참고.

## 실행 방법

### 1) 환경 준비
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) 설정
- `Root_Stream/config/config.example.yaml`를 복사해 `Root_Stream/config/config.yaml` 생성
- 필요 시 `.env`에 민감정보 설정
  - 예: `OPENAI_API_KEY`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`

### 3) CLI 실행
```bash
python -m Root_Stream.main --question "최근 24시간 장비별 에러 건수 알려줘"
```

DB 실행 포함:
```bash
python -m Root_Stream.main --execute-sql --question "최근 24시간 장비별 에러 건수 알려줘"
```

### 4) API 실행
```bash
uvicorn Root_Stream.server.api_app:app --host 127.0.0.1 --port 8000 --reload
```

### 5) Ingest 실행
기본 문서:
```bash
python -m Root_Ingest.ingest.ingest_pipeline
```

RAG 문서:
```bash
python -m Root_Ingest.ingest.ingest_pipeline --config Root_Ingest/config/config.rag.yaml
```

## 테스트 방법

### pytest (권장)
```bash
pytest
```

### unittest 호환 실행
```bash
python -m unittest discover -s tests -p "test_*.py"
```

## 모드 설명
- `natural`: 기본 시스템 프롬프트 + 질문으로 SQL 초안 생성
- `prompt`: schema/business 제약 템플릿 기반 SQL 생성
- `rag_prompt`: Chroma 검색 컨텍스트 포함 SQL 생성
- `auto`: Planner 결과 기반 자동 라우팅

## config / env 설명

### Root_Stream 주요 설정
- `mode`, `llm_provider`
- `paths.project_root`, `paths.prompt_file`, `paths.log_file`
- `retrieval.enabled`, `retrieval.chroma_path`, `retrieval.collection_name`, `retrieval.top_k`
- `database.*`
- `sql.allow_only_select`, `sql.max_rows`

### 자주 쓰는 환경변수
- `STREAM_MODE`, `LLM_PROVIDER`
- `OPENAI_MODEL`, `OPENAI_API_KEY`
- `OLLAMA_MODEL`, `OLLAMA_BASE_URL`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `LOG_LEVEL`

## 문서
- 리팩터링 분석: [docs/refactor_analysis.md](docs/refactor_analysis.md)
- LangGraph 흐름: [docs/langgraph_workflow.md](docs/langgraph_workflow.md)
- 개발 규칙: `Rule.md`
