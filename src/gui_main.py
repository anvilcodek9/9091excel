"""
로젠 엑셀 생성기 메인 GUI.
터미널 없이 실행: 토큰 설정, 조회 기간 선택, 엑셀 생성 및 결과 안내.
"""

import os
import sys
import platform
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Any

from .main import generate_logen_shipping_file
from .exceptions import NaverAPIError, DataTransformError, ExcelGenerationError


def _get_app_dir() -> str:
    """exe 실행 시 작업 디렉터리를 exe 위치로 고정 (생성 파일이 exe 옆에 저장되도록)"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BackgroundWorker:
    """백그라운드 스레드 실행을 도와주는 유틸리티 클래스 (UI 블로킹 방지)"""
    
    @staticmethod
    def run(
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


class LogenExcelApp:
    """로젠 발송 엑셀 생성기 메인 앱 애플리케이션 클래스"""

    def __init__(self):
        self.app_dir = _get_app_dir()
        os.chdir(self.app_dir)

        self.root = tk.Tk()
        self.root.title("로젠 택배 발송 엑셀 생성기")
        self.root.minsize(560, 520)

        # UI 변수 상태 선언
        self.period_mode = tk.StringVar(value="hours")
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.hours_spin_var = tk.StringVar(value="24")
        self.save_path_var = tk.StringVar(value=self.app_dir)
        self.keyword_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="대기 중 · 조회 기간을 선택하세요")

        self.root.configure(bg="#ffffff")
        self._init_default_dates()
        self._setup_style()
        self._setup_ui()
        self._center_window()

    def _init_default_dates(self):
        today = datetime.now()
        default_to = today.strftime("%Y-%m-%d")
        default_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        self.from_var.set(default_from)
        self.to_var.set(default_to)

    def _setup_style(self):
        """테마, 여백, 폰트 등 전역 스타일을 세팅합니다."""
        self.style = ttk.Style(self.root)
        if 'clam' in self.style.theme_names():
            self.style.theme_use('clam')
            
        sys_os = platform.system()
        if sys_os == 'Darwin':
            self.base_font = ('Helvetica Neue', 13)
            self.bold_font = ('Helvetica Neue', 13, 'bold')
            self.large_font = ('Helvetica Neue', 15, 'bold')
            self.title_font = ('Helvetica Neue', 22, 'bold')
        elif sys_os == 'Windows':
            self.base_font = ('Malgun Gothic', 10)
            self.bold_font = ('Malgun Gothic', 10, 'bold')
            self.large_font = ('Malgun Gothic', 12, 'bold')
            self.title_font = ('Malgun Gothic', 18, 'bold')
        else:
            self.base_font = ('sans-serif', 11)
            self.bold_font = ('sans-serif', 11, 'bold')
            self.large_font = ('sans-serif', 13, 'bold')
            self.title_font = ('sans-serif', 20, 'bold')

        bg_color = "#ffffff"
        fg_color = "#111111"
        btn_bg = "#f5f5f5"
        btn_active = "#e5e5e5"

        self.style.configure('.', font=self.base_font, background=bg_color, foreground=fg_color)
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TLabel', background=bg_color, foreground=fg_color)
        self.style.configure('TRadiobutton', background=bg_color, foreground=fg_color)
        self.style.configure('TLabelframe', background=bg_color, padding=20, borderwidth=0)
        self.style.configure('TLabelframe.Label', background=bg_color, font=self.bold_font, foreground=fg_color)
        self.style.configure('TSeparator', background="#eeeeee")
        
        self.style.configure('TButton', padding=10, font=self.base_font, background=btn_bg, borderwidth=0)
        self.style.map('TButton', background=[('active', btn_active)])
        
        # Primary Call to Action Button Style
        self.style.configure(
            'Action.TButton', 
            font=self.large_font, 
            padding=14,
            background=fg_color,
            foreground=bg_color,
            borderwidth=0
        )
        self.style.map('Action.TButton', background=[('active', '#333333'), ('disabled', '#cccccc')])

    def _setup_ui(self):
        # 전체 뼈대 패딩 충분하게 확보
        main_frame = ttk.Frame(self.root, padding="30 24 30 24")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 헤더 (타이틀) 영역
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            header_frame, 
            text="로젠 발송 데이터 추출", 
            font=self.title_font,
            foreground="#111111"
        ).pack(anchor=tk.W)
        ttk.Label(
            header_frame, 
            text="네이버 커머스 주문을 조회하여 로젠송장 양식에 맞춘 엑셀을 생성합니다.", 
            foreground="#737373"
        ).pack(anchor=tk.W, pady=(4, 0))

        # 2. 조회 설정 영역 (LabelFrame을 카테고리화)
        settings_group = ttk.LabelFrame(main_frame, text="추출 옵션 설정")
        settings_group.pack(fill=tk.X, pady=(0, 20))

        # grid 레이아웃을 사용해 폼 정렬
        settings_group.columnconfigure(1, weight=1)
        
        # 2-1. 기간 모드 선택
        row = 0
        ttk.Label(settings_group, text="조회 기준", font=self.bold_font).grid(row=row, column=0, sticky=tk.NW, pady=(0, 10), padx=(0, 20))
        
        radio_frame = ttk.Frame(settings_group)
        radio_frame.grid(row=row, column=1, sticky="w", pady=(0, 10))
        
        ttk.Radiobutton(
            radio_frame, text="최근 시간 기준", variable=self.period_mode, value="hours", command=self._on_period_mode_change
        ).pack(side=tk.LEFT, padx=(0, 16))
        
        ttk.Radiobutton(
            radio_frame, text="특정 일자 기간", variable=self.period_mode, value="range", command=self._on_period_mode_change
        ).pack(side=tk.LEFT)

        # 2-2. 동적 상세 조건 폼
        row += 1
        self.dynamic_input_frame = ttk.Frame(settings_group)
        self.dynamic_input_frame.grid(row=row, column=1, sticky="w", pady=(0, 16))
        
        # Hours Form
        self.hours_form = ttk.Frame(self.dynamic_input_frame)
        spin = ttk.Spinbox(self.hours_form, from_=1, to=168, width=5, textvariable=self.hours_spin_var)
        spin.pack(side=tk.LEFT)
        ttk.Label(self.hours_form, text="시간 전부터 현재까지", foreground="#737373").pack(side=tk.LEFT, padx=(8, 0))

        # Range Form
        self.range_form = ttk.Frame(self.dynamic_input_frame)
        ttk.Entry(self.range_form, width=12, textvariable=self.from_var).pack(side=tk.LEFT)
        ttk.Label(self.range_form, text="~").pack(side=tk.LEFT, padx=6)
        ttk.Entry(self.range_form, width=12, textvariable=self.to_var).pack(side=tk.LEFT)

        # 2-3. 제외 필터
        row += 2
        ttk.Separator(settings_group, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="we", pady=(4, 14))
        
        row += 1
        ttk.Label(settings_group, text="단어 필터링", font=self.bold_font).grid(row=row, column=0, sticky=tk.W, pady=(0, 8), padx=(0, 20))
        ttk.Entry(settings_group, textvariable=self.keyword_var, width=40).grid(row=row, column=1, sticky="w", pady=(0, 8))
        
        row += 1
        ttk.Label(settings_group, text="").grid(row=row, column=0)
        ttk.Label(
            settings_group, 
            text="입력한 단어가 상품명에 포함되면 제외합니다 (쉼표 구분)", 
            foreground="#737373"
        ).grid(row=row, column=1, sticky="w", pady=(0, 4))
        
        # 초기 모드 반영
        self._on_period_mode_change()

        # 3. 액션 & 진행 영역 통합 프레임
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.BOTH, expand=True)

        self.run_btn = ttk.Button(
            action_frame, 
            text="엑셀 파일 생성하기", 
            style="Action.TButton", 
            command=self._do_generate,
            cursor="hand2" if platform.system() != 'Darwin' else "" 
        )
        self.run_btn.pack(fill=tk.X, pady=(10, 20), ipady=8)

        # 4. 하단 상태 표시줄
        status_container = ttk.Frame(main_frame)
        status_container.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(
            status_container, 
            textvariable=self.status_var, 
            wraplength=480, 
            justify=tk.LEFT,
            foreground="#2563eb"
        )
        self.status_label.pack(side=tk.LEFT, anchor=tk.W)

        self.open_folder_btn = ttk.Button(
            status_container, text="저장 폴더 보기", command=self._open_save_folder
        )
        self.open_folder_btn.pack(side=tk.RIGHT)

    def _center_window(self):
        self.root.update_idletasks()
        w = max(self.root.winfo_reqwidth(), 560)
        h = max(self.root.winfo_reqheight(), 520)
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_period_mode_change(self):
        if self.period_mode.get() == "hours":
            self.range_form.pack_forget()
            self.hours_form.pack(fill=tk.X)
        else:
            self.hours_form.pack_forget()
            self.range_form.pack(fill=tk.X)

    def _open_save_folder(self):
        try:
            if not os.path.isdir(self.app_dir):
                messagebox.showerror("폴더 없음", f"저장 폴더를 찾을 수 없습니다.\n\n{self.app_dir}")
                return
                
            if platform.system() == 'Windows':
                os.startfile(self.app_dir)
            elif platform.system() == 'Darwin':
                import subprocess
                subprocess.Popen(['open', self.app_dir])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', self.app_dir])
        except Exception as e:
            messagebox.showerror("폴더 열기 오류", f"폴더를 열 수 없습니다.\n\n{e}")

    def _get_api_parameters(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        from_iso = None
        to_iso = None
        last_hours = None

        if self.period_mode.get() == "hours":
            try:
                last_hours = int(self.hours_spin_var.get().strip())
                last_hours = max(1, min(168, last_hours))
            except ValueError:
                raise ValueError("시간(N)란에 올바른 숫자를 입력해 주세요 (1~168).")
        else:
            try:
                from_str = self.from_var.get().strip()
                to_str = self.to_var.get().strip()
                if not from_str or not to_str:
                    raise ValueError("시작일과 종료일을 입력해 주세요. (예: 2024-03-01)")
                
                kst = timezone(timedelta(hours=9))
                start_dt = datetime.strptime(from_str, "%Y-%m-%d").replace(tzinfo=kst)
                end_dt = datetime.strptime(to_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999000, tzinfo=kst)
                
                from_iso = start_dt.isoformat(timespec="milliseconds")
                to_iso = end_dt.isoformat(timespec="milliseconds")
            except ValueError as e:
                if "입력해 주세요" in str(e):
                    raise
                raise ValueError("날짜 형식이 올바르지 않습니다. YYYY-MM-DD (예: 2024-03-01)")
                
        return from_iso, to_iso, last_hours

    def _do_generate(self):
        try:
            from_iso, to_iso, last_hours = self._get_api_parameters()
        except ValueError as e:
            self.status_label.configure(foreground="#d35400") # 오렌지색 에러 표기
            self.status_var.set(f"입력 확인 필요: {str(e)}")
            messagebox.showwarning("입력 확인 필요", str(e))
            return

        raw_keywords = self.keyword_var.get()
        exclude_keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]

        def work():
            return generate_logen_shipping_file(
                access_token=None,
                from_iso=from_iso,
                to_iso=to_iso,
                last_hours=last_hours,
                exclude_keywords=exclude_keywords,
            )

        def on_start():
            self.run_btn.state(["disabled"])
            self.run_btn.config(text="데이터 조회 및 엑셀 생성 중...")
            self.status_label.configure(foreground="#2563eb")
            self.status_var.set("API에서 주문 데이터를 가져와 변환 작업을 수행하고 있습니다.")

        def on_done():
            self.run_btn.state(["!disabled"])
            self.run_btn.config(text="엑셀 파일 생성하기")

        def on_success(path: str):
            abspath = os.path.abspath(path)
            self.status_label.configure(foreground="#059669")
            self.status_var.set(f"완료: {os.path.basename(abspath)} 생성됨")
            messagebox.showinfo("완료", f"엑셀 파일 생성이 완료되었습니다.\n\n저장 경로:\n{abspath}")

        def on_error(exc: Exception):
            if isinstance(exc, NaverAPIError):
                msg = f"API 연동 오류: {exc}"
            elif isinstance(exc, DataTransformError):
                msg = f"양식 변환 중 오류 발생: {exc}"
            elif isinstance(exc, ExcelGenerationError):
                msg = f"엑셀 생성 실패: {exc}"
            elif isinstance(exc, ValueError):
                msg = f"설정 오류: {exc}"
            else:
                msg = f"시스템 알 수 없는 오류: {str(exc) or type(exc).__name__}"
                
            self.status_label.configure(foreground="#dc2626")
            self.status_var.set(f"오류: {msg}")
            messagebox.showerror("오류 발생", msg)

        BackgroundWorker.run(
            self.root, work, on_start, on_done, on_success, on_error
        )

    def run(self):
        self.root.mainloop()


def run_gui() -> None:
    app = LogenExcelApp()
    app.run()
