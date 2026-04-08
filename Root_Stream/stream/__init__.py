# 이 파일은 STREAM 공통 데이터 모델을 외부에 노출하는 진입점입니다.
# 오케스트레이터, mode 서비스, 노트북이 동일 모델을 재사용하도록 구성합니다.
# 반환 형식 통일을 통해 mode별 결과 비교를 쉽게 합니다.
# 최종 목표인 query 중심 결과 구조를 일관되게 유지합니다.

from Root_Stream.stream.models import RetrievedContext, StreamRequest, StreamResult

__all__ = ["RetrievedContext", "StreamRequest", "StreamResult"]
