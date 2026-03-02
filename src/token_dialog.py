"""exe 실행 시 인증 정보 입력용 GUI 다이얼로그 (tkinter).

Client ID / Client Secret을 입력받아, 실행 시 토큰 자동 발급에 사용합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple

from .auth import get_access_token
from .exceptions import NaverAPIError


def show_credentials_dialog(parent: Optional[tk.Tk] = None) -> Optional[Tuple[str, str]]:
    """
    네이버 커머스 API Client ID / Client Secret을 입력받는 창을 띄웁니다.
    parent가 있으면 해당 창의 자식 Toplevel로 띄워 메인 창과 상태가 맞게 동작합니다.
    확인 시 실제 토큰 발급을 시도하고, 성공한 경우에만 (client_id, client_secret) 튜플을 반환합니다.
    취소 시 None을 반환합니다.
    """
    result: list = [None]  # Optional[Tuple[str, str]]

    def on_ok():
        cid = entry_client_id.get().strip()
        secret = entry_secret.get().strip()
        if not cid or not secret:
            messagebox.showwarning("입력 필요", "Client ID와 Client Secret을 모두 입력해 주세요.")
            return
        # 토큰 발급 시도하여 입력값 검증
        status_label.config(text="토큰 발급 확인 중…")
        dlg.update()
        try:
            get_access_token(cid, secret)
            messagebox.showinfo("인증 성공", "토큰이 정상적으로 발급되었습니다.\n인증 정보가 저장됩니다.")
            result[0] = (cid, secret)
            dlg.destroy()
        except (NaverAPIError, ValueError) as e:
            status_label.config(text="")
            msg = str(e) or type(e).__name__
            messagebox.showerror("토큰 발급 실패", f"입력한 ID/시크릿으로 토큰을 발급할 수 없습니다.\n\n{msg}")

    def on_cancel():
        result[0] = None
        dlg.destroy()

    if parent is not None:
        dlg = tk.Toplevel(parent)
        dlg.transient(parent)
        dlg.grab_set()
    else:
        dlg = tk.Tk()

    dlg.title("네이버 API 인증 설정")
    dlg.resizable(True, False)
    dlg.minsize(400, 180)

    frame = ttk.Frame(dlg, padding=14)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        frame,
        text="네이버 커머스 API 센터에서 발급한 애플리케이션 정보를 입력하세요.\n"
        "입력한 값으로 실행 시 액세스 토큰을 자동 발급합니다.",
    ).pack(anchor=tk.W, pady=(0, 10))

    ttk.Label(frame, text="Client ID (애플리케이션 ID):").pack(anchor=tk.W)
    entry_client_id = ttk.Entry(frame, width=50)
    entry_client_id.pack(fill=tk.X, pady=(2, 8))
    entry_client_id.focus_set()

    ttk.Label(frame, text="Client Secret (애플리케이션 시크릿):").pack(anchor=tk.W)
    entry_secret = ttk.Entry(frame, width=50, show="*")
    entry_secret.pack(fill=tk.X, pady=(2, 8))

    status_label = ttk.Label(frame, text="", foreground="gray")
    status_label.pack(anchor=tk.W, pady=(0, 8))

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X)
    ttk.Button(btn_frame, text="확인", command=on_ok).pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.RIGHT)

    dlg.bind("<Return>", lambda e: on_ok())
    dlg.bind("<Escape>", lambda e: on_cancel())

    dlg.update_idletasks()
    w, h = 420, 220
    if parent is not None:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
    else:
        x = (dlg.winfo_screenwidth() // 2) - (w // 2)
        y = (dlg.winfo_screenheight() // 2) - (h // 2)
    dlg.geometry(f"+{x}+{y}")

    if parent is not None:
        dlg.protocol("WM_DELETE_WINDOW", on_cancel)
        dlg.wait_window()
    else:
        dlg.mainloop()
    return result[0]


def show_token_dialog() -> Optional[str]:
    """
    (하위 호환) 토큰 입력 창.
    Client ID/Secret 방식으로 통일했으므로, 내부적으로 show_credentials_dialog를 띄우지 않고
    None을 반환합니다. 호출부는 show_credentials_dialog 사용을 권장합니다.
    """
    return None
