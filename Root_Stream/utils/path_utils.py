# 이 파일은 STREAM 모듈에서 사용하는 경로 처리 규칙을 모아둔 유틸입니다.

# 문자열 경로를 pathlib.Path로 통일해 OS 차이를 줄입니다.

# 상대 경로는 프로젝트 루트를 기준으로 해석해 재현성을 확보합니다.

# 디렉터리 자동 생성 함수를 제공해 입출력 코드를 단순화합니다.

from __future__ import annotations
from pathlib import Path


def get_project_root() -> Path:
    """
    역할:
    STREAM 경로 유틸리티에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
    
    Returns:
    Path: STREAM 경로 유틸리티 계산 결과를 `Path` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    return Path(__file__).resolve().parent.parent


def resolve_path(path_value: str | Path, base_path: Path | None = None) -> Path:
    """
    역할:
    STREAM 경로 유틸리티에서 설정값을 검증 가능한 최종 값으로 확정합니다.
    
    Args:
    path_value (str | Path):
    역할: 해석할 파일/디렉터리 경로 값입니다.
    값: `str | Path`입니다.
    전달 출처: config 값 또는 호출부 계산값이 전달됩니다.
    주의사항: 오탈자나 공백이 있으면 잘못된 위치를 참조할 수 있습니다.
    base_path (Path | None):
    역할: 상대 경로 해석 기준 경로입니다.
    값: `Path | None`입니다.
    전달 출처: 호출부에서 루트 경로를 지정할 때 전달됩니다.
    주의사항: `None`이면 내부 기본 루트 기준으로 해석됩니다.
    
    Returns:
    Path: STREAM 경로 유틸리티 계산 결과를 `Path` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    path_obj = Path(path_value)
    if path_obj.is_absolute():
        return path_obj

    if base_path is None:
        base_path = get_project_root()

    return (base_path / path_obj).resolve()


def ensure_directory(directory_path: Path) -> Path:
    """
    역할:
    STREAM 경로 유틸리티 문맥에서 `ensure_directory` 기능을 수행합니다.
    
    Args:
    directory_path (Path):
    역할: 파일 또는 디렉터리 경로를 지정합니다.
    값: 타입 힌트 기준 `Path` 값이 전달됩니다.
    전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
    주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
    
    Returns:
    Path: STREAM 경로 유틸리티 계산 결과를 `Path` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    directory_path.mkdir(parents=True, exist_ok=True)
    return directory_path
