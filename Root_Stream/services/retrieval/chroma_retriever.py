# 이 파일은 ChromaDB에서 유사 문서를 검색하는 RAG 조회 서비스를 제공합니다.

# 임베딩 벡터를 입력받아 top-k 컨텍스트를 공통 모델로 변환해 반환합니다.

# 검색 문서/점수/메타데이터를 함께 남겨 추적 가능한 RAG 흐름을 만듭니다.

# Chroma 의존성 오류와 조회 오류를 명확히 로그에 기록합니다.

from __future__ import annotations
from pathlib import Path
from typing import Any, cast
from Root_Stream.stream.models import RetrievedContext
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaRetriever:
    """Chroma PersistentClient 기반 검색 서비스입니다."""

    def __init__(self, persist_directory: Path, collection_name: str, top_k: int = 3) -> None:
        """
        역할:
        Chroma 검색에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        persist_directory (Path):
        역할: Chroma DB 영속 저장 폴더를 지정합니다.
        값: `Path` 객체입니다.
        전달 출처: config의 chroma 경로 설정에서 전달됩니다.
        주의사항: 환경별 디렉터리를 분리하지 않으면 데이터가 섞일 수 있습니다.
        collection_name (str):
        역할: Chroma 컬렉션 식별 이름입니다.
        값: 문자열입니다.
        전달 출처: config `collection_name`에서 전달됩니다.
        주의사항: 같은 이름을 재사용하면 이전 데이터와 혼합될 수 있습니다.
        top_k (int):
        역할: 검색 시 상위 몇 개 컨텍스트를 사용할지 지정합니다.
        값: 정수입니다.
        전달 출처: config `retrieval.top_k`에서 전달됩니다.
        주의사항: 값이 너무 크면 노이즈와 프롬프트 길이가 증가합니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        self.persist_directory = persist_directory

        self.collection_name = collection_name

        self.top_k = top_k

        self._collection = None

    def _get_collection(self):
        """
        역할:
        Chroma 검색에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
        
        Returns:
        Any: Chroma 검색 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        ImportError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        if self._collection is not None:
            return self._collection

        try:
            import chromadb

        except Exception as error:
            raise ImportError("RAG 모드를 사용하려면 chromadb 패키지를 설치하세요.") from error

        logger.info(

            "Chroma 컬렉션 연결 시작: path=%s, collection=%s",

            self.persist_directory,

            self.collection_name,

        )
        try:
            client = chromadb.PersistentClient(path=str(self.persist_directory))

            self._collection = client.get_or_create_collection(name=self.collection_name)

        except Exception:
            logger.exception("Chroma 컬렉션 연결 실패: collection=%s", self.collection_name)

            raise

        return self._collection

    def retrieve(self, query_embedding: list[float]) -> list[RetrievedContext]:
        """
        역할:
        Chroma 검색 문맥에서 `retrieve` 기능을 수행합니다.
        
        Args:
        query_embedding (list[float]):
        역할: 질문을 임베딩 모델로 변환한 벡터입니다.
        값: `list[float]`입니다.
        전달 출처: `embed_query()` 결과가 전달됩니다.
        주의사항: 컬렉션 벡터 차원과 다르면 검색 호출이 실패합니다.
        
        Returns:
        list[RetrievedContext]: Chroma 검색 결과를 순회 가능한 목록으로 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        collection = self._get_collection()

        logger.info("RAG 검색 시작: top_k=%d", self.top_k)
        try:
            result = collection.query(

                query_embeddings=[query_embedding],

                n_results=self.top_k,

                include=["documents", "metadatas", "distances"],

            )

        except Exception:
            logger.exception("RAG 검색 실패")

            raise

        documents = (result.get("documents") or [[]])[0]

        metadatas = (result.get("metadatas") or [[]])[0]

        distances = (result.get("distances") or [[]])[0]

        ids = (result.get("ids") or [[]])[0]

        contexts: list[RetrievedContext] = []
        for index, document in enumerate(documents):
            context = RetrievedContext(

                chunk_id=str(ids[index]) if index < len(ids) else f"unknown_{index}",

                text=str(document),

                score=float(distances[index]) if index < len(distances) and distances[index] is not None else None,

                metadata=cast(dict[str, Any], metadatas[index]) if index < len(metadatas) and isinstance(metadatas[index], dict) else {},

            )

            contexts.append(context)

        if contexts:
            sample_ids = ", ".join(item.chunk_id for item in contexts[:3])

            logger.info("RAG 검색 완료: result_count=%d, sample_ids=%s", len(contexts), sample_ids)

        else:
            logger.warning("RAG 검색 결과가 없습니다.")

        return contexts
