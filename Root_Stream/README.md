# Root Stream

`Root_Stream`은 사용자 자연어 질문을 입력받아 최종 `query`를 생성하는 STREAM 단계입니다.  
실행 방식은 `config/config.yaml`의 `mode` 값으로 제어합니다.

## 지원 Mode

- `natural_llm`: 질문을 그대로 LLM에 전달해 query 생성
- `prompt_llm`: 질문 + 템플릿 프롬프트로 query 생성
- `rag_prompt_llm`: 임베딩 + Chroma 검색 + 프롬프트 결합 후 query 생성
- `api_result`: 외부 API 결과를 기반으로 query 생성

## 기본 실행

```bash
python -m Root_Stream.main --question "최근 경고 로그 100건을 조회해줘"
```

## 설정 파일

`Root_Stream/config/config.yaml`에서 아래 항목을 관리합니다.

- `mode`
- `llm_provider` (`ollama` / `openai`)
- `ollama.model`, `ollama.base_url`
- `openai.model`, `openai.api_key`
- `retrieval.enabled`, `retrieval.chroma_path`, `retrieval.collection_name`, `retrieval.top_k`
- `prompts.active_prompt`
- `api.endpoint`, `api.timeout`
- `logging.level`

## 프롬프트 관리

프롬프트는 `Root_Stream/prompts/prompt_templates.yaml`에서 중앙 관리하며,  
`PromptManager`가 key 기반 조회/렌더링을 담당합니다.

## 노트북

- `notebooks/01_natural_llm.ipynb`
- `notebooks/02_prompt_llm.ipynb`
- `notebooks/03_rag_prompt_llm.ipynb`
- `notebooks/04_api_result.ipynb`

노트북은 설명용 Markdown + 모듈 재사용 코드 셀로 구성되어 있습니다.

## SQL 실행 단계 (신규)

LLM/RAG/API로 이미 생성된 SQL 문자열을 MSSQL에 안전하게 조회·실행하는 독립 레이어가 추가되었습니다.  
기존 `main.py`의 `mode` 분기 로직은 그대로 두고, 필요에 따라 아래 모듈을 호출해 사용합니다.

- `services/sql/sql_guard.py`: 조회용 SQL 검증(SELECT/WITH 허용, 위험한 키워드 차단)
- `services/sql/mssql_client.py`: MSSQL 연결 및 `pandas.DataFrame` 반환
- `services/sql/sql_executor_service.py`: guard -> DB 실행 -> `max_rows` 제한 적용
- `services/sql/sql_execution_integration.py`: 외부에서 생성된 query를 실행하는 통합 헬퍼

### 실행 예시 (CLI)

예시: 이미 LLM으로 생성된 query를 실행하려면

```bash
python -m Root_Stream.main --execute-sql --question "최근 경고 로그 100건을 조회해줘"
```

또는 직접 SQL 문자열을 전달해 실행:

```bash
python -m Root_Stream.main --execute-sql --sql "SELECT TOP 100 * FROM Logs WHERE level = 'Warning'"
```

### Notebook 테스트

- `notebooks/05_mssql_sql_execution.ipynb`
- 공통 `SqlExecutorService`를 import하여 config 기반으로 동일 로직을 테스트합니다.
