# 이 파일은 질의 텍스트를 임베딩 벡터로 변환하는 서비스를 제공합니다.

# RAG mode에서만 사용되며 sentence-transformers 모델을 로딩합니다.

# 모델명/디바이스는 config로 받아 하드코딩을 피합니다.

# 임베딩 생성 실패 시 원인을 로깅하고 예외를 상위로 전달합니다.

from __future__ import annotations
from typing import Any
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class SentenceTransformerEmbeddingService:
    """sentence-transformers 기반 질의 임베딩 서비스입니다."""

    def __init__(self, model_name: str, device: str | None = None) -> None:
        """
        역할:
        질의 임베딩 생성에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        model_name (str):
        역할: 리소스/모델/프롬프트의 이름 식별자입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `질의 임베딩 생성` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        device (str | None):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str | None` 값이 전달됩니다.
        전달 출처: `질의 임베딩 생성` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        self.model_name = model_name

        self.device = device

        self._model: Any | None = None

    def _get_model(self) -> Any:
        """
        역할:
        질의 임베딩 생성에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
        
        Returns:
        Any: 질의 임베딩 생성 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        ImportError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer

        except Exception as error:
            raise ImportError("RAG 모드를 사용하려면 sentence-transformers 패키지를 설치하세요.") from error

        logger.info("임베딩 모델 로드 시작: model=%s", self.model_name)

        self._model = SentenceTransformer(self.model_name, device=self.device)

        logger.info("임베딩 모델 로드 완료: model=%s", self.model_name)
        return self._model

    def embed_query(self, query_text: str) -> list[float]:
        """
        역할:
        질의 임베딩 생성 문맥에서 `embed_query` 기능을 수행합니다.
        
        Args:
        query_text (str):
        역할: `embed_query` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `질의 임베딩 생성` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        list[float]: 질의 임베딩 생성 결과를 순회 가능한 목록으로 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        model = self._get_model()

        logger.info("질의 임베딩 시작: text_length=%d", len(query_text))
        try:
            vector = model.encode(query_text, normalize_embeddings=True)

        except Exception:
            logger.exception("질의 임베딩 생성 실패")

            raise

        return [float(value) for value in vector]
