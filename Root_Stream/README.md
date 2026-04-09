# Root_Stream

`Root_Stream`은 질문을 받아 SQL을 생성하는 실행 레이어입니다.  
실행 모드는 `config/config.yaml`의 `mode`로 선택합니다.

## 지원 모드
- `natural_llm`: 질문을 그대로 LLM에 전달
- `prompt_llm`: 프롬프트 템플릿(`query_generation_prompt`)을 사용
- `rag_prompt_llm`: Chroma 검색 결과를 프롬프트에 결합

`api_result` 모드는 현재 코드에서 제거되었고 지원하지 않습니다.

## 실행
프로젝트 루트에서:

```bash
python -m Root_Stream.main --question "최근 30일간 설비별 오류 건수를 보여줘"
```

SQL 생성 후 DB 실행까지 포함:

```bash
python -m Root_Stream.main --execute-sql --question "최근 30일간 설비별 오류 건수를 보여줘"
```

## 설정
1. `Root_Stream/config/config.example.yaml`을 `Root_Stream/config/config.yaml`로 복사
2. DB/LLM 값을 채움
3. 민감정보는 `.env` 또는 OS 환경변수로 오버라이드

환경변수 오버라이드 주요 키:
- `STREAM_MODE`, `LLM_PROVIDER`
- `OLLAMA_MODEL`, `OLLAMA_BASE_URL`
- `OPENAI_MODEL`, `OPENAI_API_KEY`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `LOG_LEVEL`

## 프롬프트
- 파일: `Root_Stream/prompts/prompt_templates.yaml`
- 관리 클래스: `Root_Stream/prompts/prompt_manager.py`
- `prompt_llm`, `rag_prompt_llm`에서 아래 값은 `config.yaml`의 `prompts` 섹션에서 주입:
  - `schema_context`
  - `business_rules`
  - `additional_constraints`

## 노트북
- `notebooks/01_natural_llm.ipynb`
- `notebooks/02_prompt_llm.ipynb`
- `notebooks/03_rag_prompt_llm.ipynb`

노트북은 실험용이며, 서비스 로직은 `services/` 아래 `.py` 모듈을 사용합니다.

## 서버
FastAPI 서버 실행:

```bash
uvicorn Root_Stream.server.api_app:app --host 127.0.0.1 --port 8000 --reload
```

테스트 요청:

```bash
python -m Root_Stream.server.debug_client --mode rag_prompt --question "최근 경고 로그 50건"
```
