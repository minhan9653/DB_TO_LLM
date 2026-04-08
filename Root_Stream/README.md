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


## SQL ���� �ܰ�(�ű�)

LLM/RAG/API�� �̹� ������ SQL ���ڿ��� MSSQL�� �����ϰ� ��ȸ �����ϴ� ���� ���̾ �߰��Ǿ����ϴ�.  
���� `main.py` / mode �б� ������ �������� �ʾҰ�, �Ʒ� ����� ���������� ȣ���ϸ� �˴ϴ�.

- `services/sql/sql_guard.py`: ��ȸ�� SQL ����(SELECT/WITH ���, ���� Ű���� ����)
- `services/sql/mssql_client.py`: MSSQL ���� �� DataFrame ��ȸ
- `services/sql/sql_executor_service.py`: guard -> DB ���� -> max_rows ���� ����
- `services/sql/sql_execution_integration.py`: ���� ���� ���(query) ���� ����

### ���� ����(CLI)

```bash
```

�Ǵ� �̹� ������ SQL�� ���� ����:

```bash
```

### Notebook �׽�Ʈ

- `notebooks/05_mssql_sql_execution.ipynb`
- ���� `SqlExecutorService`�� import�ؼ� config ������� ���� ������ �׽�Ʈ�մϴ�.
