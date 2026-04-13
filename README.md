# DB_TO_LLM

자연어 질문을 **Planner → LangGraph** 파이프라인으로 처리하는 DB/RAG 통합 응답 시스템.

사용자의 질문 1개가 입력되면 Planner가 먼저 실행되어 질문 유형과 실행 계획을 결정한다.  
이후 LangGraph 노드 오케스트레이션이 SQL 조회, 문서 검색, 일반 답변 흐름을 분기해 실행한다.

---

## 주요 특징

- **Planner 우선 실행**: LLM이 질문을 분석해 `DB_ONLY`, `RAG_ONLY`, `GENERAL`, `DB_THEN_RAG` 등 6가지 query_type 중 하나를 결정
- **LangGraph 오케스트레이션**: 모든 분기 흐름이 상태 머신(StateGraph)으로 관리됨
- **SELECT-only SQL 보안**: 금지 키워드(INSERT/UPDATE/DELETE/DROP 등) 차단, 마크다운 코드블록 자동 제거
- **통합 설정**: `config/config.yaml` 단일 파일로 LLM, DB, ChromaDB, 임베딩 모두 관리
- **다중 LLM 지원**: Ollama(기본), OpenAI(선택) 지원, config로 전환

---

## 폴더 구조

```text
DB_TO_LLM/
├── config/
│   └── config.yaml              # 전체 설정 파일 (LLM, DB, RAG, ingest 공통)
├── src/
│   └── db_to_llm/               # 단일 패키지 루트
│       ├── shared/
│       │   ├── config/           # config_loader.py
│       │   ├── logging/          # logger.py
│       │   └── llm/              # base_llm, llm_factory, ollama_client, openai_client
│       ├── ingest/               # 문서 수집 → 파싱 → 청킹 → 임베딩 → ChromaDB 저장
│       │   ├── parsers/
│       │   ├── document_loader.py
│       │   ├── chunk_service.py
│       │   ├── embedding_service.py
│       │   ├── vector_store_service.py
│       │   └── ingest_pipeline.py
│       └── stream/
│           ├── planner/          # LLM 기반 query_type 결정
│           │   ├── models.py
│           │   ├── plan_validator.py
│           │   └── planner_service.py
│           ├── graph/            # LangGraph 그래프 정의
│           │   ├── state.py
│           │   ├── builder.py
│           │   └── runner.py
│           ├── nodes/            # 실행 노드 (각 1개 함수)
│           │   ├── planner_node.py
│           │   ├── router.py
│           │   ├── generate_sql_node.py
│           │   ├── validate_sql_node.py
│           │   ├── execute_sql_node.py
│           │   ├── summarize_db_node.py
│           │   ├── retrieve_rag_node.py
│           │   ├── general_answer_node.py
│           │   └── final_answer_node.py
│           ├── services/         # 기능별 서비스 (LLM, SQL, RAG, Prompt)
│           ├── prompts/          # prompt_manager.py + prompt_templates.yaml
│           ├── api/              # FastAPI 앱 (POST /api/query)
│           └── cli/              # CLI 진입점
├── notebooks/
│   ├── ingest/
│   │   └── 01_build_vectorstore.ipynb
│   └── stream/
│       ├── 01_planner_test.ipynb
│       └── 02_end_to_end_graph_flow.ipynb
└── tests/
    └── stream/
        ├── unit/
        │   ├── test_planner.py
        │   ├── test_sql_validator.py
        │   └── test_router.py
        └── integration/
            ├── test_db_then_rag.py
            ├── test_rag_only.py
            └── test_final_answer.py
```

---

## 실행 흐름

```
사용자 질문
  └── planner_node     ← LLM이 query_type, steps 결정
       └── route_by_query_type
            ├── DB 경로 (DB_ONLY / DB_THEN_RAG / DB_THEN_GENERAL)
            │    generate_sql → validate_sql → execute_sql → summarize_db
            │         └── DB_THEN_RAG: → retrieve_rag → final_answer
            │         └── 기타: → final_answer
            ├── RAG 경로 (RAG_ONLY / RAG_THEN_GENERAL)
            │    retrieve_rag → final_answer
            └── GENERAL 경로
                 general_answer → final_answer
```

### query_type 목록

| query_type | 설명 |
|---|---|
| `DB_ONLY` | SQL 조회만 필요한 질문 |
| `RAG_ONLY` | 문서 검색만 필요한 질문 |
| `GENERAL` | SQL/RAG 없이 LLM이 직접 답변 |
| `DB_THEN_RAG` | DB 조회 후 그 결과를 기반으로 문서 검색 |
| `DB_THEN_GENERAL` | DB 조회 후 LLM 종합 답변 |
| `RAG_THEN_GENERAL` | 문서 검색 후 LLM 종합 답변 |

---

## 환경 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. config/config.yaml 수정

```yaml
llm_provider: ollama          # "ollama" 또는 "openai"

ollama:
  base_url: http://localhost:11434
  model: qwen2.5:14b

database:
  driver: "ODBC Driver 17 for SQL Server"
  server: YOUR_DB_SERVER
  database: YOUR_DB_NAME
  username: YOUR_USERNAME
  password: YOUR_PASSWORD         # 또는 환경변수 DB_PASSWORD 사용

retrieval:
  chroma_path: data/chroma
  collection_name: doc_chunks
  embedding_model: paraphrase-multilingual-MiniLM-L12-v2
  top_k: 5
```

환경변수로 설정 오버라이드 가능:

```bash
set DB_PASSWORD=비밀번호
set OPENAI_API_KEY=sk-xxx
```

### 3. PYTHONPATH 설정

```bash
set PYTHONPATH=c:\Users\minha\DB_TO_LLM
```

또는 `pip install -e .` 사용 시 자동 처리됨.

---

## 실행 방법

### API 서버 실행

```bash
uvicorn src.db_to_llm.stream.api.app:app --reload --port 8000
```

요청 예시:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "지난달 매출 상위 10개 제품을 알려줘"}'
```

응답 형식:

```json
{
  "question": "지난달 매출 상위 10개 제품을 알려줘",
  "query_type": "DB_ONLY",
  "final_answer": "...",
  "generated_sql": "SELECT ...",
  "validated_sql": "SELECT ...",
  "db_rows": [[...]],
  "db_summary": "...",
  "retrieved_contexts": [],
  "errors": [],
  "trace_logs": ["planner_node: ...", "generate_sql_node: ..."]
}
```

### CLI 실행

```bash
python -m src.db_to_llm.stream.cli.main --question "지난달 매출 상위 10개 제품은?" --pretty
```

---

## Ingest (문서 벡터 저장)

문서 파일을 ChromaDB에 적재하려면:

```bash
python -c "
from src.db_to_llm.ingest.ingest_pipeline import run_ingest_pipeline
result = run_ingest_pipeline()
print(result)
"
```

또는 노트북 실행:

```
notebooks/ingest/01_build_vectorstore.ipynb
```

---

## 테스트 실행

```bash
# 전체 테스트
pytest tests/stream/ -v

# 단위 테스트만
pytest tests/stream/unit/ -v

# 통합 테스트만
pytest tests/stream/integration/ -v

# 특정 파일
pytest tests/stream/unit/test_sql_validator.py -v
```

---

## 노트북 목록

| 노트북 | 설명 |
|---|---|
| [notebooks/ingest/01_build_vectorstore.ipynb](notebooks/ingest/01_build_vectorstore.ipynb) | 문서 수집 → ChromaDB 저장 전체 흐름 |
| [notebooks/stream/01_planner_test.ipynb](notebooks/stream/01_planner_test.ipynb) | Planner 테스트 (다양한 query_type 시나리오) |
| [notebooks/stream/02_end_to_end_graph_flow.ipynb](notebooks/stream/02_end_to_end_graph_flow.ipynb) | End-to-End 그래프 실행 테스트 |

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
