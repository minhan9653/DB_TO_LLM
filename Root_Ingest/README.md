# Root_Ingest

`Root_Ingest`는 스키마/업무 문서를 RAG 검색 가능한 벡터 데이터로 만드는 단계입니다.

## 하는 일
1. 문서 로드 (`doc/`)
2. 파싱 (`docling` / `marker` / `unstructured`)
3. 청킹
4. 임베딩 생성
5. Chroma 저장

## 실행
프로젝트 루트에서:

```bash
python -m Root_Ingest.ingest.ingest_pipeline
```

## 설정
파일: `Root_Ingest/config/config.yaml`

주요 항목:
- `parsing.parser`: `docling | marker | unstructured`
- `chunking.chunk_size`, `chunking.chunk_overlap`
- `embedding.model_name`
- `vector_store.collection_name`

환경변수 오버라이드:
- `EMBEDDING_MODEL_NAME`
- `CHROMA_COLLECTION_NAME`
- `CHROMA_PERSIST_DIR`
- `LOG_LEVEL`

## 노트북
- `notebooks/01_document_load.ipynb`
- `notebooks/02_parse.ipynb`
- `notebooks/03_chunk.ipynb`
- `notebooks/04_embed.ipynb`
- `notebooks/05_vector_store.ipynb`
- `notebooks/06_end_to_end_test.ipynb`

노트북은 실험/검증용이고, 실제 로직은 `ingest/` 아래 모듈을 사용합니다.
