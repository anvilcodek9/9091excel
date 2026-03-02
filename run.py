"""
exe 실행용 엔트리 포인트.
이 파일을 PyInstaller로 패키징하여 단일 exe로 배포합니다.
기간 지정: --from "2024-03-01T00:00:00" --to "2024-03-02T00:00:00" 또는 --hours 12
"""
import argparse
import os
import sys

# PyInstaller 번들에서 src 패키지 인식
sys.path.insert(0, ".")


def _stderr_msg(*parts: str) -> None:
    """한글 등 비ASCII가 있어도 stderr에 안전히 출력 (latin-1 환경 대비)."""
    msg = "".join(parts) + "\n"
    sys.stderr.buffer.write(msg.encode("utf-8", errors="replace"))
    sys.stderr.buffer.flush()


def _has_env_credentials() -> bool:
    """환경 변수로 토큰 또는 client_id/secret이 설정되어 있는지 확인."""
    if os.environ.get("NAVER_ACCESS_TOKEN", "").strip():
        return True
    if os.environ.get("NAVER_CLIENT_ID", "").strip() and os.environ.get("NAVER_CLIENT_SECRET", "").strip():
        return True
    return False


def main_cli():
    """CLI 모드: 명령줄 인자로 기간 지정 후 엑셀 생성 (개발/자동화용)."""
    from src.main import generate_logen_shipping_file
    from src.exceptions import NaverAPIError, DataTransformError, ExcelGenerationError

    parser = argparse.ArgumentParser(description="네이버 스마트스토어 주문 → 로젠 발송 엑셀 생성")
    parser.add_argument("--from", dest="from_iso", metavar="ISO", help="조회 시작 시각 (ISO-8601, 예: 2024-03-01T00:00:00)")
    parser.add_argument("--to", dest="to_iso", metavar="ISO", help="조회 종료 시각 (ISO-8601). --from과 함께 사용, 최대 24시간 구간")
    parser.add_argument("--hours", type=int, metavar="N", help="최근 N시간 기준 조회 (--from/--to 미지정 시 사용, 기본 24)")
    args = parser.parse_args()

    # 환경 변수에 인증 정보가 없으면 Client ID/Secret 입력 창 표시
    if not _has_env_credentials():
        from src.token_dialog import show_credentials_dialog
        creds = show_credentials_dialog()
        if not creds or not creds[0] or not creds[1]:
            _stderr_msg("Client ID / Client Secret이 입력되지 않았거나 취소되었습니다.")
            return 1
        os.environ["NAVER_CLIENT_ID"] = creds[0]
        os.environ["NAVER_CLIENT_SECRET"] = creds[1]

    try:
        path = generate_logen_shipping_file(
            access_token=None,
            from_iso=args.from_iso or None,
            to_iso=args.to_iso or None,
            last_hours=args.hours,
        )
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


def main():
    # 인자가 없으면 GUI 실행 (exe 더블클릭 또는 python run.py)
    if len(sys.argv) == 1:
        from src.gui_main import run_gui
        run_gui()
        return 0
    return main_cli()


if __name__ == "__main__":
    sys.exit(main())
