# Root Ingest

## Parser selection (config only)

`config/config.yaml`에서 아래 값만 바꾸면 파서를 교체할 수 있습니다.

```yaml
parsing:
  parser: docling # docling | marker | unstructured
  options:
    extract_tables: true
    extract_images: false
    language: ko
    text_encodings:
      - utf-8
      - utf-8-sig
      - cp949
      - euc-kr
```

## Run

```bash
python -m Root_Ingest.ingest.ingest_pipeline
```

## Optional parser dependencies

- docling: `pip install docling`
- marker: `pip install marker-pdf`
- unstructured: `pip install "unstructured[all-docs]"`

선택한 파서가 설치되지 않은 경우 ingest 시작 시 명확한 ImportError 메시지를 출력합니다.
