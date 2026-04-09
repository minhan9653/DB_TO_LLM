# Root_Ingest

`Root_Ingest`는 문서를 파싱/청크/임베딩해서 Chroma 벡터 저장소로 적재하는 모듈입니다.

## 기본 흐름
1. 문서 수집 (`doc_dir`)
2. 파싱 (`docling | marker | unstructured`)
3. 청크 분할
4. 임베딩 생성
5. Chroma 저장

## 실행 방법
기본(DB 관련 문서) 설정으로 실행:

```bash
python -m Root_Ingest.ingest.ingest_pipeline
```

RAG 전용 문서 설정으로 실행:

```bash
python -m Root_Ingest.ingest.ingest_pipeline --config Root_Ingest/config/config.rag.yaml
```

## 문서 폴더 분리
- DB 관련 문서: `Root_Ingest/doc/`
- RAG 전용 문서: `Root_Ingest/doc_rag/`

## 설정 파일
- 기본: `Root_Ingest/config/config.yaml`
- RAG 전용: `Root_Ingest/config/config.rag.yaml`

`config.rag.yaml`은 출력 경로를 `data_rag/*`로 분리하고, 컬렉션명을 `rag_chunks`로 사용합니다.

## 주요 설정 키
- `paths.doc_dir`
- `paths.chroma_dir`
- `vector_store.collection_name`
- `embedding.model_name`
- `chunking.chunk_size`, `chunking.chunk_overlap`

## 환경변수 오버라이드
- `EMBEDDING_MODEL_NAME`
- `CHROMA_COLLECTION_NAME`
- `CHROMA_PERSIST_DIR`
- `LOG_LEVEL`
