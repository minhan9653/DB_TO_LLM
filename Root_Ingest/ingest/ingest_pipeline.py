# This module runs the full ingest pipeline from documents to vector store.
# Each stage stays isolated so notebook testing remains straightforward.
# Parser choice is now config-driven via parsing.parser without code edits.
# Downstream chunking/embedding/vector logic is intentionally preserved.

from __future__ import annotations
from pathlib import Path
from typing import Any
from Root_Ingest.ingest.chunk_service import chunk_documents
from Root_Ingest.ingest.document_loader import collect_documents, save_documents_to_jsonl
from Root_Ingest.ingest.embedding_service import create_embeddings
from Root_Ingest.ingest.parser_service import parse_documents
from Root_Ingest.ingest.vector_store_service import upsert_embeddings_to_chroma
from Root_Ingest.ingest.parsers.factory import normalize_parser_name
from Root_Ingest.utils.config_loader import load_config
from Root_Ingest.utils.logger import get_logger, setup_logger
from Root_Ingest.utils.path_utils import ensure_directory, resolve_path

logger = get_logger(__name__)


def run_ingest_pipeline(config_path: Path) -> dict[str, Any]:
    """
    역할:
    INGEST 파이프라인 실행 흐름을 실행하고 후속 단계에서 사용할 결과를 조합해 반환합니다.
    
    Args:
    config_path (Path):
    역할: 로드할 설정 파일 위치를 지정합니다.
    값: `Path` 형식의 파일 경로입니다.
    전달 출처: CLI `--config` 값 또는 상위 실행 코드에서 전달됩니다.
    주의사항: 상대 경로일 때 실행 위치에 따라 다른 파일을 읽을 수 있어 `resolve()` 결과 확인이 필요합니다.
    
    Returns:
    dict[str, Any]: INGEST 파이프라인 실행 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    config = load_config(config_path)
    project_root = resolve_path(config.get("paths", {}).get("project_root", "."), config_path.parent.parent)
    _configure_logging(config, project_root)

    doc_dir = resolve_path(config["paths"]["doc_dir"], project_root)
    parsed_dir = ensure_directory(resolve_path(config["paths"]["parsed_dir"], project_root))
    chunks_dir = ensure_directory(resolve_path(config["paths"]["chunks_dir"], project_root))
    embeddings_dir = ensure_directory(resolve_path(config["paths"]["embeddings_dir"], project_root))
    chroma_dir = ensure_directory(resolve_path(config["paths"]["chroma_dir"], project_root))

    parser_name, parser_options = _resolve_parsing_config(config)

    logger.info("파이프라인 시작")
    logger.info("입력 폴더: %s", doc_dir)
    logger.info("Selected parser: %s", parser_name)

    documents = collect_documents(doc_dir, config["document_loader"]["supported_extensions"])
    save_documents_to_jsonl(documents, parsed_dir / "document_index.jsonl")

    parsed_documents = parse_documents(
        documents=documents,
        output_path=parsed_dir / "parsed_documents.jsonl",
        parser_name=parser_name,
        parser_options=parser_options,
    )

    chunks = chunk_documents(
        parsed_documents=parsed_documents,
        chunk_size=int(config["chunking"]["chunk_size"]),
        chunk_overlap=int(config["chunking"]["chunk_overlap"]),
        output_path=chunks_dir / "chunks.jsonl",
    )

    embeddings = create_embeddings(
        chunks=chunks,
        model_name=config["embedding"]["model_name"],
        batch_size=int(config["embedding"]["batch_size"]),
        normalize_embeddings=bool(config["embedding"]["normalize_embeddings"]),
        device=config["embedding"].get("device"),
        output_path=embeddings_dir / "embeddings.jsonl",
    )

    stored_count = upsert_embeddings_to_chroma(
        embeddings=embeddings,
        persist_directory=chroma_dir,
        collection_name=config["vector_store"]["collection_name"],
        batch_size=int(config["vector_store"]["batch_size"]),
    )

    summary = {
        "document_count": len(documents),
        "parsed_document_count": len(parsed_documents),
        "chunk_count": len(chunks),
        "embedding_count": len(embeddings),
        "stored_vector_count": stored_count,
    }
    logger.info("파이프라인 완료: %s", summary)
    return summary


def _configure_logging(config: dict[str, Any], project_root: Path) -> None:
    """
    역할:
    INGEST 파이프라인 실행 문맥에서 `_configure_logging` 기능을 수행합니다.
    
    Args:
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    project_root (Path):
    역할: 상대 경로를 해석할 기준 프로젝트 루트입니다.
    값: `Path` 객체입니다.
    전달 출처: config의 `paths.project_root`를 `resolve_path()`로 해석한 값이 전달됩니다.
    주의사항: 루트가 잘못되면 로그, prompt, chroma 경로가 모두 어긋납니다.
    
    Returns:
    None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file_value = config.get("paths", {}).get("log_file")
    log_file_path = None
    if log_file_value:
        log_file_path = resolve_path(log_file_value, project_root)
    setup_logger(log_level=log_level, log_file_path=log_file_path)


def _resolve_parsing_config(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """
    역할:
    INGEST 파이프라인 실행에서 설정값을 검증 가능한 최종 값으로 확정합니다.
    
    Args:
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    
    Returns:
    tuple[str, dict[str, Any]]: INGEST 파이프라인 실행 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    parsing_config = config.get("parsing", {})
    raw_parser_name = parsing_config.get("parser", "docling")
    parser_name = normalize_parser_name(str(raw_parser_name))

    parser_options = parsing_config.get("options", {})
    if not isinstance(parser_options, dict):
        parser_options = {}

    # Backward compatibility for old config schema: parser.text_encodings
    legacy_text_encodings = config.get("parser", {}).get("text_encodings")
    if legacy_text_encodings and "text_encodings" not in parser_options:
        parser_options["text_encodings"] = legacy_text_encodings

    return parser_name, parser_options

if __name__ == "__main__":
    default_config_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    run_ingest_pipeline(default_config_path)
