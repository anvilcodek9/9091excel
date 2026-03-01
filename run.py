"""
exe 실행용 엔트리 포인트.
이 파일을 PyInstaller로 패키징하여 단일 exe로 배포합니다.
"""
import sys

# PyInstaller 번들에서 src 패키지 인식
sys.path.insert(0, ".")


def _stderr_msg(*parts: str) -> None:
    """한글 등 비ASCII가 있어도 stderr에 안전히 출력 (latin-1 환경 대비)."""
    msg = "".join(parts) + "\n"
    sys.stderr.buffer.write(msg.encode("utf-8", errors="replace"))
    sys.stderr.buffer.flush()


def main():
    from src.main import generate_logen_shipping_file
    from src.exceptions import NaverAPIError, DataTransformError, ExcelGenerationError

    try:
        path = generate_logen_shipping_file()
        print(f"생성 완료: {path}")
        return 0
    except ValueError as e:
        _stderr_msg(f"설정 오류: {e}")
        _stderr_msg(
            "인증 정보를 확인하세요. "
            "NAVER_ACCESS_TOKEN 또는 NAVER_CLIENT_ID/NAVER_CLIENT_SECRET을 설정해야 합니다."
        )
        return 1
    except NaverAPIError as e:
        _stderr_msg(f"API 오류: {e}")
        return 1
    except DataTransformError as e:
        _stderr_msg(f"데이터 변환 오류: {e}")
        return 1
    except ExcelGenerationError as e:
        _stderr_msg(f"Excel 생성 오류: {e}")
        return 1
    except RuntimeError as e:
        _stderr_msg(f"실행 오류: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
