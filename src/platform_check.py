"""윈도우 플랫폼 체크 모듈"""
import os
import platform
import sys


def ensure_windows_platform():
    """
    현재 플랫폼이 Windows인지 확인합니다.
    개발/테스트 시 Mac·Linux에서 실행하려면 환경 변수 ALLOW_NON_WINDOWS=1 을 설정하세요.
    
    Raises:
        RuntimeError: Windows가 아닌 플랫폼에서 실행될 경우 (ALLOW_NON_WINDOWS 미설정 시)
    """
    if platform.system() == 'Windows':
        return
    if os.environ.get("ALLOW_NON_WINDOWS") == "1":
        return
    raise RuntimeError("이 프로그램은 Windows에서만 실행됩니다.")
