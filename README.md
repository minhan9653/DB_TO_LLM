# DB_TO_LLM

한국어 질문을 MSSQL 조회 SQL로 생성하는 프로젝트입니다.  
구성은 크게 `Root_Ingest`(문서 인제스트)와 `Root_Stream`(질문→SQL 생성)로 분리되어 있습니다.

## 프로젝트 구조
- `Root_Ingest/`: 문서 파싱, 청킹, 임베딩, Chroma 적재
- `Root_Stream/`: 모드별 SQL 생성, SQL 검증/실행, API 서버
- `Planner/`: 질문 1개를 실행 계획(JSON)으로 분해하는 실험 모듈
- `docs/`: 부가 문서/산출물

## 지원 모드 (Root_Stream)
- `natural_llm`
- `prompt_llm`
- `rag_prompt_llm`

`api_result`는 현재 코드에서 지원하지 않습니다.

## 빠른 시작
1. 가상환경 생성/활성화
2. 패키지 설치
3. `Root_Stream/config/config.example.yaml`을 복사해 `config.yaml` 생성
4. 필요 시 `.env`에 민감정보 설정
5. 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m Root_Stream.main --question "최근 30일간 설비별 오류 건수를 보여줘"
```

SQL 실행까지 하려면:

```bash
python -m Root_Stream.main --execute-sql --question "최근 30일간 설비별 오류 건수를 보여줘"
```

## 설정 원칙
- 기본값: `config.yaml`
- 민감정보/환경별 값: `.env` 또는 OS 환경변수로 오버라이드
- 지원 환경변수는 `.env.example`에 정리되어 있습니다.

## RAG 사용 흐름
1. `Root_Ingest`로 문서 인제스트 실행
2. `Root_Stream`에서 `mode: rag_prompt_llm`로 실행

```bash
python -m Root_Ingest.ingest.ingest_pipeline
python -m Root_Stream.main --question "최근 30일간 알람 상위 5개를 보여줘"
```

## API 서버
```bash
uvicorn Root_Stream.server.api_app:app --host 127.0.0.1 --port 8000 --reload
```

## 테스트
외부 LLM/DB 없이 실행 가능한 최소 단위 테스트:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## 문서
- 전체/빠른 시작: 이 README
- Stream 상세: `Root_Stream/README.md`
- Ingest 상세: `Root_Ingest/README.md`
- 개발 규칙: `Rule.md`
