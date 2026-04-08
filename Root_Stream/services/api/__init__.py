# 이 파일은 외부 API 연동 서비스의 공개 진입점을 제공합니다.
# api_result mode는 이 서비스만 통해 외부 API를 호출합니다.
# 호출/후처리 로직을 mode 파일에서 분리해 유지보수를 단순화합니다.
# 향후 API 타입 추가 시 이 패키지 내부 확장만으로 대응할 수 있습니다.

from Root_Stream.services.api.external_api_service import ExternalApiService

__all__ = ["ExternalApiService"]
