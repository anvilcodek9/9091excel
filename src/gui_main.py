"""
로젠 엑셀 생성기 메인 GUI.
터미널 없이 실행: 토큰 설정, 조회 기간 선택, 엑셀 생성 및 결과 안내.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Any

# exe 실행 시 작업 디렉터리를 exe 위치로 고정 (생성 파일이 exe 옆에 저장되도록)
def _get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _has_env_credentials() -> bool:
    if os.environ.get("NAVER_ACCESS_TOKEN", "").strip():
        return True
    if os.environ.get("NAVER_CLIENT_ID", "").strip() and os.environ.get("NAVER_CLIENT_SECRET", "").strip():
        return True
    return False


def _run_in_background(
    root: tk.Tk,
    fn: Callable[[], Any],
    on_start: Callable[[], None],
    on_done: Callable[[], None],
    on_success: Callable[[Any], None],
    on_error: Callable[[Exception], None],
) -> None:
    result: list = [None]
    error_holder: list = [None]

    def worker():
        try:
            result[0] = fn()
        except Exception as e:
            error_holder[0] = e

    def on_worker_done():
        on_done()
        if error_holder[0] is not None:
            on_error(error_holder[0])
        else:
            on_success(result[0])

    def poll():
        if not t.is_alive():
            on_worker_done()
            return
        root.after(100, poll)

    on_start()
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    root.after(100, poll)


def run_gui() -> None:
    from .main import generate_logen_shipping_file
    from .exceptions import NaverAPIError, DataTransformError, ExcelGenerationError
    from .token_dialog import show_credentials_dialog

    app_dir = _get_app_dir()
    # 생성 파일이 exe와 같은 폴더에 저장되도록
    os.chdir(app_dir)

    root = tk.Tk()
    root.title("로젠 발송 엑셀 생성기")
    root.resizable(True, True)
    root.minsize(420, 380)

    # 스타일
    main_pad = 16
    section_pad = (0, 12)

    main = ttk.Frame(root, padding=main_pad)
    main.pack(fill=tk.BOTH, expand=True)

    # ---- 인증 ----
    auth_frame = ttk.LabelFrame(main, text="인증", padding=8)
    auth_frame.pack(fill=tk.X, pady=section_pad)

    token_status = tk.StringVar(value="환경 변수 미설정 — 아래 [인증 설정]에서 Client ID / Secret을 입력하세요.")
    if _has_env_credentials():
        token_status.set("환경 변수로 인증 정보가 설정되어 있습니다.")

    ttk.Label(auth_frame, textvariable=token_status, wraplength=400).pack(anchor=tk.W)
    stored_client_id: list = [None]  # Optional[str]
    stored_client_secret: list = [None]  # Optional[str]

    def open_credentials_dialog():
        creds = show_credentials_dialog(parent=root)
        if creds and creds[0] and creds[1]:
            stored_client_id[0], stored_client_secret[0] = creds[0], creds[1]
            token_status.set("✓ 토큰 발급 확인됨 — 인증 정보가 저장되었습니다. (엑셀 생성 시 토큰 자동 발급)")
            root.update_idletasks()
        else:
            stored_client_id[0], stored_client_secret[0] = None, None
            if not _has_env_credentials():
                token_status.set("인증 정보가 입력되지 않았습니다. [인증 설정]에서 Client ID / Secret을 입력하세요.")
            root.update_idletasks()

    ttk.Button(auth_frame, text="인증 설정", command=open_credentials_dialog).pack(anchor=tk.W, pady=(6, 0))

    # ---- 조회 기간 ----
    period_frame = ttk.LabelFrame(main, text="조회 기간", padding=8)
    period_frame.pack(fill=tk.X, pady=section_pad)

    period_mode = tk.StringVar(value="hours")
    from_var = tk.StringVar()
    to_var = tk.StringVar()

    today = datetime.now()
    default_to = today.strftime("%Y-%m-%d")
    default_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    from_var.set(default_from)
    to_var.set(default_to)

    def on_period_mode_change():
        if period_mode.get() == "hours":
            hours_frame.pack(fill=tk.X)
            range_frame.pack_forget()
        else:
            hours_frame.pack_forget()
            range_frame.pack(fill=tk.X)

    ttk.Radiobutton(
        period_frame,
        text="최근 N시간 기준",
        variable=period_mode,
        value="hours",
        command=on_period_mode_change,
    ).pack(anchor=tk.W)
    hours_frame = ttk.Frame(period_frame)
    hours_frame.pack(fill=tk.X)
    hours_spin_var = tk.StringVar(value="24")
    ttk.Spinbox(hours_frame, from_=1, to=168, width=6, textvariable=hours_spin_var).pack(side=tk.LEFT, padx=(20, 6))
    ttk.Label(hours_frame, text="시간 (1~168)").pack(side=tk.LEFT)

    ttk.Radiobutton(
        period_frame,
        text="기간 지정 (시작일 ~ 종료일, 해당일 00:00~24:00)",
        variable=period_mode,
        value="range",
        command=on_period_mode_change,
    ).pack(anchor=tk.W, pady=(8, 0))
    range_frame = ttk.Frame(period_frame)
    ttk.Label(range_frame, text="시작일:").pack(side=tk.LEFT, padx=(20, 4))
    from_entry = ttk.Entry(range_frame, width=12, textvariable=from_var)
    from_entry.pack(side=tk.LEFT, padx=(0, 12))
    ttk.Label(range_frame, text="종료일:").pack(side=tk.LEFT, padx=(0, 4))
    to_entry = ttk.Entry(range_frame, width=12, textvariable=to_var)
    to_entry.pack(side=tk.LEFT)
    ttk.Label(range_frame, text="  (예: 2024-03-01)").pack(side=tk.LEFT, padx=(4, 0))

    on_period_mode_change()

    # ---- 저장 위치 (표시용) ----
    save_frame = ttk.Frame(main)
    save_frame.pack(fill=tk.X, pady=section_pad)
    ttk.Label(save_frame, text="저장 위치:").pack(side=tk.LEFT)
    save_path_var = tk.StringVar(value=app_dir)
    ttk.Label(save_frame, textvariable=save_path_var, foreground="gray").pack(side=tk.LEFT, padx=(4, 0))

    # ---- 실행 버튼 ----
    run_btn = ttk.Button(main, text="엑셀 생성", command=None)
    run_btn.pack(pady=(8, 0))

    # ---- 상태/결과 ----
    status_var = tk.StringVar(value="대기 중입니다. 조회 기간을 선택한 뒤 [엑셀 생성]을 누르세요.")
    status_label = ttk.Label(main, textvariable=status_var, wraplength=400, justify=tk.LEFT)
    status_label.pack(anchor=tk.W, pady=(12, 0))

    def open_save_folder():
        """엑셀 저장 폴더(프로그램 위치)를 파일 탐색기로 연다."""
        try:
            if not os.path.isdir(app_dir):
                messagebox.showerror("폴더 없음", f"저장 폴더를 찾을 수 없습니다.\n\n{app_dir}")
                return
            os.startfile(app_dir)
        except OSError as e:
            messagebox.showerror("폴더 열기 오류", f"저장 폴더를 열 수 없습니다.\n\n{app_dir}\n\n{e}")

    open_folder_btn = ttk.Button(main, text="저장 폴더 열기", command=open_save_folder)
    open_folder_btn.pack(anchor=tk.W, pady=(6, 0))

    def apply_stored_credentials():
        """GUI에서 입력한 Client ID/Secret을 이번 실행을 위해 환경 변수에 넣습니다."""
        if stored_client_id[0] and stored_client_secret[0]:
            os.environ["NAVER_CLIENT_ID"] = stored_client_id[0]
            os.environ["NAVER_CLIENT_SECRET"] = stored_client_secret[0]

    def do_generate():
        has_stored = bool(stored_client_id[0] and stored_client_secret[0])
        if not _has_env_credentials() and not has_stored:
            messagebox.showwarning("인증 필요", "[인증 설정]에서 Client ID와 Client Secret을 입력해 주세요.")
            return
        # GUI에서 방금 입력한 ID/시크릿이 있으면 환경 변수에 넣어 이번 실행에 사용
        apply_stored_credentials()

        from_iso = None
        to_iso = None
        last_hours = None

        if period_mode.get() == "hours":
            try:
                last_hours = int(hours_spin_var.get().strip())
                last_hours = max(1, min(168, last_hours))
            except ValueError:
                messagebox.showerror("입력 오류", "시간에는 1~168 사이 숫자를 입력해 주세요.")
                return
        else:
            try:
                from_str = from_var.get().strip()
                to_str = to_var.get().strip()
                if not from_str or not to_str:
                    messagebox.showerror("입력 오류", "시작일과 종료일을 입력해 주세요. (예: 2024-03-01)")
                    return
                # API는 유효한 ISO-8601(시간대 포함)을 요구함. KST(+09:00) + 밀리초로 통일
                kst = timezone(timedelta(hours=9))
                start_dt = datetime.strptime(from_str, "%Y-%m-%d").replace(tzinfo=kst)
                end_dt = datetime.strptime(to_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999000, tzinfo=kst)
                from_iso = start_dt.isoformat(timespec="milliseconds")
                to_iso = end_dt.isoformat(timespec="milliseconds")
                # 날짜 유효성 (이미 strptime으로 검증됨)
            except ValueError as e:
                messagebox.showerror("입력 오류", "날짜 형식이 올바르지 않습니다. YYYY-MM-DD (예: 2024-03-01)")
                return

        def work():
            return generate_logen_shipping_file(
                access_token=None,
                from_iso=from_iso,
                to_iso=to_iso,
                last_hours=last_hours,
            )

        def on_start():
            run_btn.state(["disabled"])
            status_var.set("주문 조회 및 엑셀 생성 중…")

        def on_done():
            run_btn.state(["!disabled"])

        def on_success(path: str):
            abspath = os.path.abspath(path)
            # 상태 영역은 짧게 표시하고, 전체 경로는 알림창으로 보여준다.
            status_var.set(f"완료: {os.path.basename(abspath)}\n엑셀 파일이 생성되었습니다. [저장 폴더 열기] 버튼으로 폴더를 확인하세요.")
            messagebox.showinfo("완료", f"엑셀 파일이 생성되었습니다.\n\n{abspath}")

        def on_error(exc: Exception):
            if isinstance(exc, NaverAPIError):
                msg = f"API 오류: {exc}"
            elif isinstance(exc, DataTransformError):
                msg = f"데이터 변환 오류: {exc}"
            elif isinstance(exc, ExcelGenerationError):
                msg = f"엑셀 생성 오류: {exc}"
            elif isinstance(exc, ValueError):
                msg = f"설정 오류: {exc}"
            else:
                msg = str(exc) or type(exc).__name__
            status_var.set(f"오류: {msg}")
            messagebox.showerror("오류", msg)

        _run_in_background(root, work, on_start, on_done, on_success, on_error)

    run_btn.configure(command=do_generate)

    # 창 중앙 배치
    root.update_idletasks()
    w, h = 480, 460
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    root.mainloop()
