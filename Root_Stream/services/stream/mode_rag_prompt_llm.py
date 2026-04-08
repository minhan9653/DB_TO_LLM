# 이 파일은 rag_prompt_llm mode 실행 로직을 담당합니다.

# 질문 임베딩 생성 후 Chroma에서 유사 컨텍스트를 조회합니다.

# 검색 결과와 프롬프트 템플릿을 결합해 LLM 입력을 구성합니다.

# RAG 검색 근거를 결과 모델에 포함해 검증 가능한 흐름을 제공합니다.

from __future__ import annotations
from pathlib import Path
from typing import Any
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.services.retrieval.chroma_retriever import ChromaRetriever
from Root_Stream.services.retrieval.embedding_service import SentenceTransformerEmbeddingService
from Root_Stream.stream.models import RetrievedContext, StreamRequest, StreamResult
from Root_Stream.utils.logger import get_logger
from Root_Stream.utils.path_utils import resolve_path

logger = get_logger(__name__)


def run_rag_prompt_llm_mode(

    *,

    request: StreamRequest,

    config: dict[str, Any],

    prompt_manager: PromptManager,

    llm_client: BaseLLMClient,

    project_root: Path,

) -> StreamResult:
    """
    역할:
    STREAM rag_prompt_llm 모드 흐름을 실행하고 후속 단계에서 사용할 결과를 조합해 반환합니다.
    
    Args:
    request (StreamRequest):
    역할: 사용자 질문을 포함한 STREAM 요청 모델입니다.
    값: `StreamRequest` 인스턴스입니다.
    전달 출처: `StreamOrchestrator.run()` 또는 테스트 코드에서 생성되어 전달됩니다.
    주의사항: `request.question`이 비어 있으면 하위 모드에서 오류가 날 수 있습니다.
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    prompt_manager (PromptManager):
    역할: 프롬프트 키 조회와 템플릿 렌더링을 수행합니다.
    값: `PromptManager` 인스턴스입니다.
    전달 출처: `build_stream_orchestrator()`에서 생성되어 전달됩니다.
    주의사항: 템플릿 변수 누락 시 `KeyError`가 발생할 수 있습니다.
    llm_client (BaseLLMClient):
    역할: 모델 provider별 텍스트 생성을 수행합니다.
    값: `BaseLLMClient` 구현체(`OllamaClient`/`OpenAIClient`)입니다.
    전달 출처: `create_llm_client(config)` 결과가 전달됩니다.
    주의사항: 모델명, 엔드포인트, API 키 설정이 맞지 않으면 호출 예외가 전파됩니다.
    project_root (Path):
    역할: 상대 경로를 해석할 기준 프로젝트 루트입니다.
    값: `Path` 객체입니다.
    전달 출처: config의 `paths.project_root`를 `resolve_path()`로 해석한 값이 전달됩니다.
    주의사항: 루트가 잘못되면 로그, prompt, chroma 경로가 모두 어긋납니다.
    
    Returns:
    StreamResult: query, metadata, retrieved_context를 포함한 STREAM 표준 결과를 반환합니다.
    
    Raises:
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    logger.info("mode 실행 시작: rag_prompt_llm")

    retrieval_config = config.get("retrieval", {})
    if not bool(retrieval_config.get("enabled", False)):
        raise ValueError("retrieval.enabled=false 상태에서는 rag_prompt_llm 모드를 실행할 수 없습니다.")

    embedding_model = str(

        retrieval_config.get(

            "embedding_model",

            config.get("embedding", {}).get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),

        )

    )

    chroma_path = resolve_path(retrieval_config["chroma_path"], project_root)
        
    collection_name = str(retrieval_config["collection_name"])

    top_k = int(retrieval_config.get("top_k", 3))

    embedding_service = SentenceTransformerEmbeddingService(model_name=embedding_model)

    retriever = ChromaRetriever(

        persist_directory=chroma_path,

        collection_name=collection_name,

        top_k=top_k,

    )

    query_embedding = embedding_service.embed_query(request.question)

    contexts = retriever.retrieve(query_embedding)

    context_block = _build_context_block(contexts)

    system_prompt = prompt_manager.get_prompt("default_system_prompt")

    prompt_key = "rag_query_generation_prompt"

    user_prompt = prompt_manager.render_prompt(

        prompt_key,

        {

            "question": request.question,

            "retrieved_context": context_block,

        },

    )

    query = llm_client.generate(system_prompt=system_prompt, user_prompt=user_prompt)

    result = StreamResult(

        mode="rag_prompt_llm",

        question=request.question,

        query=query,

        llm_provider=llm_client.provider_name,

        prompt_key=prompt_key,

        retrieved_contexts=contexts,

        metadata={

            "mode": config.get("mode"),

            "llm_provider": config.get("llm_provider"),

            "retrieved_count": len(contexts),

            "collection_name": collection_name,

        },

    )

    logger.info("mode 실행 완료: rag_prompt_llm")
    return result


def _build_context_block(contexts: list[RetrievedContext]) -> str:
    """
    역할:
    STREAM rag_prompt_llm 모드 문맥에서 `_build_context_block` 기능을 수행합니다.
    
    Args:
    contexts (list[RetrievedContext]):
    역할: `_build_context_block` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[RetrievedContext]` 값이 전달됩니다.
    전달 출처: `STREAM rag_prompt_llm 모드` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    if not contexts:
        return "검색된 컨텍스트가 없습니다."

    lines: list[str] = []
    for index, item in enumerate(contexts, start=1):
        lines.append(f"[{index}] chunk_id={item.chunk_id}, score={item.score}")

        lines.append(item.text)

        lines.append("")

    return "\n".join(lines).strip()
