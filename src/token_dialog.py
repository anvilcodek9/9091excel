"""exe 실행 시 인증 정보 입력용 GUI 다이얼로그 (tkinter).

Client ID / Client Secret을 입력받아, 실행 시 토큰 자동 발급에 사용합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple
import platform

from .auth import get_access_token
from .exceptions import NaverAPIError


class CredentialsDialog:
    """네이버 API 인증 정보를 입력받는 다이얼로그 래퍼 클래스"""
    
    def __init__(self, parent: Optional[tk.Tk] = None):
        self.result: list = [None]  # Optional[Tuple[str, str]]
        self.parent = parent
        
        if parent is not None:
            self.dlg = tk.Toplevel(parent)
            self.dlg.transient(parent)
            self.dlg.grab_set()
        else:
            self.dlg = tk.Tk()
            
        self._setup_style()
        self._setup_ui()
        self._center_window()
        
    def _setup_style(self):
        style = ttk.Style(self.dlg)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        # 시스템에 맞는 기본 폰트 설정
        sys_os = platform.system()
        if sys_os == 'Darwin':
            base_font = ('Helvetica Neue', 13)
            bold_font = ('Helvetica Neue', 13, 'bold')
        elif sys_os == 'Windows':
            base_font = ('Malgun Gothic', 10)
            bold_font = ('Malgun Gothic', 10, 'bold')
        else:
            base_font = ('sans-serif', 11)
            bold_font = ('sans-serif', 11, 'bold')

        bg_color = "#ffffff"
        fg_color = "#111111"
        btn_bg = "#f5f5f5"
        btn_active = "#e5e5e5"

        style.configure('.', font=base_font, background=bg_color, foreground=fg_color)
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', padding=2, background=bg_color, foreground=fg_color)
        style.configure('TButton', font=base_font, padding=8, background=btn_bg, borderwidth=0)
        style.map('TButton', background=[('active', btn_active)])
        
        style.configure('Primary.TButton', font=bold_font, padding=10, background=fg_color, foreground=bg_color)
        style.map('Primary.TButton', background=[('active', '#333333')])
        
    def _setup_ui(self):
        self.dlg.title("네이버 API 인증 설정")
        self.dlg.resizable(False, False) # 사이즈 고정
        self.dlg.configure(bg="#ffffff")

        # 전체 컨테이너 여백 강화
        main_frame = ttk.Frame(self.dlg, padding="30 30 30 24")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 타이틀 및 설명
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 24))
        
        ttk.Label(
            header_frame,
            text="네이버 커머스 API 연동",
            font=(ttk.Style().lookup('.', 'font')[0], 18, 'bold')
        ).pack(anchor=tk.W)
        
        ttk.Label(
            header_frame,
            text="애플리케이션 센터에서 발급한 인증 정보를 입력해 주세요.\n최초 1회 입력 시 자동 저장됩니다.",
            foreground="#737373"
        ).pack(anchor=tk.W, pady=(4, 0))

        # 입력 폼 
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X)
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Client ID").grid(row=0, column=0, sticky=tk.W, pady=(0, 10), padx=(0, 12))
        self.entry_client_id = ttk.Entry(form_frame, width=40)
        self.entry_client_id.grid(row=0, column=1, sticky="we", pady=(0, 10))
        self.entry_client_id.focus_set()

        ttk.Label(form_frame, text="Client Secret").grid(row=1, column=0, sticky=tk.W, pady=(0, 8), padx=(0, 12))
        self.entry_secret = ttk.Entry(form_frame, width=40, show="•")
        self.entry_secret.grid(row=1, column=1, sticky="we", pady=(0, 8))

        # 상태 메시지
        self.status_label = ttk.Label(main_frame, text="", foreground="#737373")
        self.status_label.pack(anchor=tk.W, pady=(8, 12))

        # 버튼 영역
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            btn_frame, text="연동 확인", style="Primary.TButton", command=self._on_ok
        ).pack(side=tk.RIGHT, padx=(8, 0))
        
        ttk.Button(
            btn_frame, text="취소", command=self._on_cancel
        ).pack(side=tk.RIGHT)

        self.dlg.bind("<Return>", lambda e: self._on_ok())
        self.dlg.bind("<Escape>", lambda e: self._on_cancel())
        
        if self.parent is not None:
            self.dlg.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_window(self):
        self.dlg.update_idletasks()
        # 창 크기 자동 계산 후 중앙 배치
        w = self.dlg.winfo_reqwidth()
        h = self.dlg.winfo_reqheight()
        
        # 여백을 주어 강제로 좀 더 넓게 설정 (Win/Mac 호환)
        w = max(w, 480)
        h = max(h, 280)
        
        if self.parent is not None:
            x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (w // 2)
            y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (h // 2)
        else:
            x = (self.dlg.winfo_screenwidth() // 2) - (w // 2)
            y = (self.dlg.winfo_screenheight() // 2) - (h // 2)
        self.dlg.geometry(f"{w}x{h}+{x}+{y}")

    def _on_ok(self):
        cid = self.entry_client_id.get().strip()
        secret = self.entry_secret.get().strip()
        if not cid or not secret:
            messagebox.showwarning("입력 필요", "Client ID와 Client Secret을 모두 입력해 주세요.")
            return

        self.status_label.config(text="토큰 발급 확인 중…", foreground="#2563eb")
        self.dlg.update()
        
        try:
            get_access_token(cid, secret)
            messagebox.showinfo("인증 성공", "토큰이 정상적으로 발급되었습니다.\n인증 정보가 안전하게 복호화되어 저장됩니다.")
            self.result[0] = (cid, secret)
            self.dlg.destroy()
        except (NaverAPIError, ValueError) as e:
            msg = str(e) or type(e).__name__
            self.status_label.config(text=f"오류: {msg}", foreground="#dc2626")
            messagebox.showerror("토큰 발급 실패", f"입력한 ID/시크릿으로 토큰을 발급할 수 없습니다.\n\n{msg}")

    def _on_cancel(self):
        self.result[0] = None
        self.dlg.destroy()

    def show(self) -> Optional[Tuple[str, str]]:
        if self.parent is not None:
            self.dlg.wait_window()
        else:
            self.dlg.mainloop()
        return self.result[0]


def show_credentials_dialog(parent: Optional[tk.Tk] = None) -> Optional[Tuple[str, str]]:
    """
    네이버 커머스 API Client ID / Client Secret을 입력받는 창을 띄웁니다.
    """
    dialog = CredentialsDialog(parent)
    return dialog.show()


def show_token_dialog() -> Optional[str]:
    return None
