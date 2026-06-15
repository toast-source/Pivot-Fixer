import os
import sys
import glob
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog

# PyInstaller 환경에서 tkinterdnd2 라이브러리 경로 설정
if getattr(sys, 'frozen', False):
    os.environ['TKDND_LIBRARY'] = os.path.join(sys._MEIPASS, 'tkinterdnd2')

from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk, ImageChops

class PivotFixerApp:
    def __init__(self, root):
        self.root = root
        self.version = "v0.3.1"
        self.root.title(f"PNG 피봇 보정 툴 (Pixel Art Optimizer) - {self.version}")

        self.root.geometry("1400x850")
        self.root.minsize(1200, 750)
        self.root.resizable(True, True)

        # 시스템 변수들 (윈도우/테마 설정)
        self.is_dark_mode = tk.BooleanVar(value=False)
        self.is_always_on_top = tk.BooleanVar(value=False)
        self.window_alpha = tk.DoubleVar(value=1.0)

        # 파일 데이터 구조: {"id": id, "path": path, "name": name, "checked": bool, "settings": dict}
        self.file_data = []
        self.preview_path = None
        self.output_dir = ""
        self.last_generated_files = [] 

        # UI 컨트롤 설정 변수들 (Spinbox 타이핑 즉시 감지를 위해 StringVar로 변경)
        self.offset_y = tk.StringVar(value="0")
        self.offset_x = tk.StringVar(value="0")
        self.h_align = tk.BooleanVar(value=True)
        self.trim_margin_x = tk.BooleanVar(value=False)
        
        self.overwrite = tk.BooleanVar(value=False)
        self.save_mode = tk.StringVar(value="original") 

        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)
        self.rotate_angle = tk.StringVar(value="0도 (회전 없음)")
        self.transform_order = tk.StringVar(value="before")

        self.tk_orig = None
        self.tk_res = None
        self._resize_timer = None
        self._offset_timer = None
        self._is_updating_ui = False
        self._current_selected_items = ()
        
        # 변수 변경 시 자동 저장 트리거 연결
        self.offset_y.trace_add("write", self._on_offset_change)
        self.offset_x.trace_add("write", self._on_offset_change)
        self.h_align.trace_add("write", self._on_var_change)
        self.trim_margin_x.trace_add("write", self._on_var_change)
        self.flip_h.trace_add("write", self._on_var_change)
        self.flip_v.trace_add("write", self._on_var_change)
        self.rotate_angle.trace_add("write", self._on_var_change)
        self.transform_order.trace_add("write", self._on_var_change)

        # UI 생성 사이클
        self.setup_menu()
        self.setup_ui()
        self.apply_theme() # 테마 초기화 적용
        
    def _on_var_change(self, *args):
        """UI에 연결된 변수값이 변경될 때마다 자동으로 호출됩니다."""
        if self._is_updating_ui: return
        self.on_ui_change()
        
    def _on_offset_change(self, *args):
        """오프셋 Spinbox 타이핑 시 너무 잦은 업데이트를 방지하기 위한 디바운싱 처리"""
        if self._is_updating_ui: return
        if self._offset_timer:
            self.root.after_cancel(self._offset_timer)
        self._offset_timer = self.root.after(80, self._apply_offset_change)
        
    def _apply_offset_change(self):
        self.on_ui_change()

    def get_colors(self):
        """다크모드 여부에 따라 동적으로 컬러 팔레트를 반환합니다."""
        if self.is_dark_mode.get():
            return {
                "BG_COLOR": "#1E1E1E",
                "PANEL_BG": "#252526",
                "PRIMARY_COLOR": "#6366F1",
                "PRIMARY_HOVER": "#4F46E5",
                "SUCCESS_COLOR": "#10B981",
                "SUCCESS_HOVER": "#059669",
                "DANGER_COLOR": "#F87171",
                "TEXT_COLOR": "#E5E7EB",
                "TEXT_MUTED": "#9CA3AF",
                "BORDER_COLOR": "#3E3E42"
            }
        else:
            return {
                "BG_COLOR": "#F0F2F5",
                "PANEL_BG": "#FFFFFF",
                "PRIMARY_COLOR": "#4F46E5",
                "PRIMARY_HOVER": "#4338CA",
                "SUCCESS_COLOR": "#10B981",
                "SUCCESS_HOVER": "#059669",
                "DANGER_COLOR": "#EF4444",
                "TEXT_COLOR": "#1E293B",
                "TEXT_MUTED": "#64748B",
                "BORDER_COLOR": "#E2E8F0"
            }

    def _update_tree_item(self, f):
        """파일 정보 딕셔너리 f를 바탕으로 Treeview의 행(체크여부, 이름, 요약텍스트, 색상)을 일괄 갱신합니다."""
        check_str = "☑" if f["checked"] else "☐"
        summary = self.format_settings_summary(f["settings"])
        tag = "modified" if summary != "━ [ 기본값 ]" else "default"
        self.tree.item(f["id"], values=(check_str, f["name"], summary), tags=(tag,))

    def apply_theme(self):
        """가져온 컬러 팔레트를 모든 ttk 위젯과 tkinter 캔버스 등에 덮어씌웁니다."""
        c = self.get_colors()
        self.root.configure(bg=c["BG_COLOR"])
        
        style = ttk.Style(self.root)
        style.theme_use("clam")

        default_font = ("Malgun Gothic", 10)
        bold_font = ("Malgun Gothic", 10, "bold")
        title_font = ("Malgun Gothic", 11, "bold")

        style.configure(".", font=default_font, background=c["BG_COLOR"], foreground=c["TEXT_COLOR"])

        style.configure("TFrame", background=c["BG_COLOR"])
        style.configure("Panel.TFrame", background=c["PANEL_BG"])

        style.configure("TLabelframe", background=c["PANEL_BG"], borderwidth=1, bordercolor=c["BORDER_COLOR"], relief="flat")
        style.configure("TLabelframe.Label", background=c["PANEL_BG"], foreground=c["PRIMARY_COLOR"], font=title_font, padding=(10, 5))

        style.configure("TLabel", background=c["PANEL_BG"], foreground=c["TEXT_COLOR"], font=default_font)
        style.configure("Muted.TLabel", background=c["PANEL_BG"], foreground=c["TEXT_MUTED"], font=("Malgun Gothic", 9))
        style.configure("Danger.TLabel", background=c["PANEL_BG"], foreground=c["DANGER_COLOR"], font=bold_font)
        style.configure("Success.TLabel", background=c["PANEL_BG"], foreground=c["SUCCESS_COLOR"], font=bold_font)

        style.configure("TCheckbutton", background=c["PANEL_BG"], foreground=c["TEXT_COLOR"], font=default_font, indicatorsize=16)
        style.map("TCheckbutton", background=[("active", c["PANEL_BG"])])

        style.configure("TRadiobutton", background=c["PANEL_BG"], foreground=c["TEXT_COLOR"], font=default_font, indicatorsize=16)
        style.map("TRadiobutton", background=[("active", c["PANEL_BG"])])

        style.configure("TCombobox", padding=5, font=default_font, bordercolor=c["BORDER_COLOR"], fieldbackground=c["PANEL_BG"], background=c["PANEL_BG"], foreground=c["TEXT_COLOR"])
        style.configure("TSpinbox", padding=5, font=default_font, bordercolor=c["BORDER_COLOR"], fieldbackground=c["PANEL_BG"], background=c["PANEL_BG"], foreground=c["TEXT_COLOR"], arrowcolor=c["TEXT_COLOR"])

        btn_bg = "#333333" if self.is_dark_mode.get() else "#F8FAFC"
        btn_active = "#444444" if self.is_dark_mode.get() else "#E2E8F0"
        style.configure("TButton", font=default_font, padding=(10, 5), background=btn_bg, borderwidth=1, bordercolor=c["BORDER_COLOR"], relief="flat", foreground=c["TEXT_COLOR"])
        style.map("TButton", background=[("active", btn_active)])

        style.configure("Primary.TButton", font=bold_font, padding=(10, 5), background=c["PRIMARY_COLOR"], foreground="white", borderwidth=0, relief="flat")
        style.map("Primary.TButton", background=[("active", c["PRIMARY_HOVER"])], foreground=[("active", "white")])

        style.configure("Success.TButton", font=("Malgun Gothic", 12, "bold"), padding=(10, 8), background=c["SUCCESS_COLOR"], foreground="white", borderwidth=0, relief="flat")
        style.map("Success.TButton", background=[("active", c["SUCCESS_HOVER"])], foreground=[("active", "white")])

        tree_bg = "#1E1E1E" if self.is_dark_mode.get() else "#FFFFFF"
        tree_head_bg = "#2D2D30" if self.is_dark_mode.get() else "#F8FAFC"
        tree_sel_bg = "#37373D" if self.is_dark_mode.get() else "#EEF2FF"
        tree_sel_fg = "#A5B4FC" if self.is_dark_mode.get() else c["PRIMARY_COLOR"]
        
        style.configure("Treeview", font=default_font, rowheight=30, background=tree_bg, fieldbackground=tree_bg, foreground=c["TEXT_COLOR"], borderwidth=0)
        style.configure("Treeview.Heading", font=bold_font, background=tree_head_bg, foreground=c["TEXT_COLOR"], borderwidth=1, bordercolor=c["BORDER_COLOR"], padding=5)
        style.map("Treeview", background=[('selected', tree_sel_bg)], foreground=[('selected', tree_sel_fg)])
        
        # 트리 폰트 태그 재설정
        self.tree.tag_configure("modified", foreground=c["DANGER_COLOR"], font=("Malgun Gothic", 10, "bold"))
        self.tree.tag_configure("default", foreground=c["TEXT_COLOR"], font=("Malgun Gothic", 10))

        scroll_bg = "#444" if self.is_dark_mode.get() else "#CBD5E1"
        scroll_trough = tree_head_bg
        style.configure("TScrollbar", background=scroll_bg, troughcolor=scroll_trough, borderwidth=0, arrowsize=12, relief="flat")
        style.map("TScrollbar", background=[("active", "#666" if self.is_dark_mode.get() else "#94A3B8")])

        # Canvas 및 하위 위젯 갱신
        if hasattr(self, 'canvas_orig') and self.canvas_orig:
            self.canvas_orig.configure(bg=c["PANEL_BG"], highlightbackground=c["BORDER_COLOR"])
            self.canvas_res.configure(bg=c["PANEL_BG"], highlightbackground=c["BORDER_COLOR"])
            self.update_preview()

        if hasattr(self, 'lbl_input_info') and self.lbl_input_info:
            self.lbl_input_info.configure(foreground=c["PRIMARY_COLOR"])

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 설정 메뉴
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ 설정", menu=settings_menu)
        
        settings_menu.add_checkbutton(label="다크 모드 적용", variable=self.is_dark_mode, command=self.apply_theme)
        settings_menu.add_checkbutton(label="항상 맨 위에 띄우기", variable=self.is_always_on_top, command=self.toggle_always_on_top)
        settings_menu.add_separator()
        settings_menu.add_command(label="창 투명도 조절...", command=self.show_transparency_dialog)

        # 도움말 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ 도움말", menu=help_menu)
        help_menu.add_command(label="사용 설명서 (매뉴얼)", command=self.show_manual)
        
    def toggle_always_on_top(self):
        """선택 시 창이 항상 최상단에 고정되도록 합니다."""
        self.root.attributes('-topmost', self.is_always_on_top.get())

    def show_transparency_dialog(self):
        """슬라이더(Scale)를 이용해 창 투명도를 직관적이고 실시간으로 조절합니다."""
        trans_win = tk.Toplevel(self.root)
        trans_win.title("투명도 조절")
        trans_win.geometry("300x120")
        trans_win.resizable(False, False)
        if self.is_always_on_top.get():
            trans_win.attributes('-topmost', True)
        
        c = self.get_colors()
        trans_win.configure(bg=c["PANEL_BG"])
        
        lbl = ttk.Label(trans_win, text="슬라이더를 움직여 투명도를 조절하세요\n(0.1 ~ 1.0)", justify="center", font=("Malgun Gothic", 10))
        lbl.pack(pady=(15, 5))
        
        def on_slider_change(val):
            alpha = float(val)
            self.window_alpha.set(alpha)
            self.root.attributes('-alpha', alpha)
            
        slider = ttk.Scale(trans_win, from_=0.1, to=1.0, orient="horizontal", command=on_slider_change)
        slider.set(self.window_alpha.get())
        slider.pack(fill="x", padx=30, pady=10)

    def show_manual(self):
        """사용 설명서를 팝업 창에 띄워줍니다."""
        manual_win = tk.Toplevel(self.root)
        manual_win.title("Pivot Fixer 사용 설명서")
        manual_win.geometry("750x650")
        manual_win.minsize(500, 400)
        # 매뉴얼 창도 메인 윈도우와 동일한 최상단 속성 부여
        if self.is_always_on_top.get():
            manual_win.attributes('-topmost', True)
        
        c = self.get_colors()
        manual_win.configure(bg=c["BG_COLOR"])
        
        txt = tk.Text(manual_win, font=("Malgun Gothic", 10), wrap="word", bg=c["PANEL_BG"], fg=c["TEXT_COLOR"], padx=20, pady=20, borderwidth=0)
        txt.pack(expand=True, fill="both", padx=10, pady=10)
        
        manual_text = """[ 🎨 PNG 피봇 보정 툴 (Pivot Fixer) 사용 설명서 ]

1. 개요
게임 개발, 스프라이트 애니메이션 프레임 작업 시 캐릭터나 오브젝트의 
'피봇(발밑 기준점)'을 캔버스 정중앙에 정확하게 맞춰주는 전문 최적화 툴입니다.

2. 작업 파일 목록 (다중 파일 제어)
- 윈도우 탐색기나 바탕화면에서 이미지를 리스트 창으로 '드래그 앤 드롭' 하세요.
- 일반 폴더처럼 Ctrl이나 Shift를 누른 채 클릭하여 여러 파일을 [다중 선택(파란색)] 할 수 있습니다.
- 목록에서 파일 이름을 더블클릭하면 툴 내부에서 즉시 새 이름으로 변경 예약이 가능합니다.

3. ⚡ 실시간 자동 설정 연동 (가장 중요)
- 목록에서 파일(들)을 파란색으로 선택해둔 상태로 상단의 '보정 및 변환 설정'을 만져보세요.
- '적용' 버튼을 누를 필요 없이 선택된 파일들의 설정값이 변경된 값으로 즉각 자동 저장됩니다.
- 각 파일마다 완전히 다른 오프셋이나 회전값을 개별적으로 줄 수 있습니다.

4. 캔버스 자동 확장 및 방어 시스템
- 처리된 이미지가 엔진에서 잘리지 않도록, 결과물은 기본적으로 원본의 2배 크기(정사각형)로 안전하게 확장됩니다.
- 피봇값을 엄청 크게(+100) 밀어서 이미지가 화면 밖으로 나가려 할 경우, 툴이 이를 감지하고 스스로 캔버스 크기를 3배, 4배로 넓혀 픽셀 손실을 방지합니다.

5. 메인 작업 실행 및 저장 옵션
- [원본 파일 덮어쓰기]: 대량의 프레임을 작업할 때 매우 추천합니다. 빠른 덮어쓰기 후 기존 이름을 유지합니다.
- [단일 폴더 취합]: 여러 폴더에 흩어져 있던 이미지들을 한 폴더에 쫙 모아서 이름 뒤에 '_pivotfix'를 붙여 뽑아줍니다.
- [마지막 작업 되돌리기]: 방금 생성된 새 파일들을 즉시 삭제(복구)해 줍니다. 단, 원본 덮어쓰기 모드에서는 사용할 수 없습니다.

* 문의나 버그 제보는 개발팀으로 언제든지 전달해 주세요!"""
        
        txt.insert("1.0", manual_text)
        txt.config(state="disabled")
    def get_current_ui_settings(self):
        """현재 UI에 입력된 설정값을 딕셔너리로 반환합니다 (문자열 값은 정수로 안전하게 캐스팅)"""
        try:
            oy = int(self.offset_y.get() or 0)
        except (ValueError, TypeError):
            oy = 0

        try:
            ox = int(self.offset_x.get() or 0)
        except (ValueError, TypeError):
            ox = 0

        return {
            "offset_y": oy,
            "offset_x": ox,
            "h_align": self.h_align.get(),
            "trim_margin_x": self.trim_margin_x.get(),
            "flip_h": self.flip_h.get(),
            "flip_v": self.flip_v.get(),
            "rotate_angle": self.rotate_angle.get(),
            "transform_order": self.transform_order.get()
        }

    def format_settings_summary(self, s):
        parts = []
        if s["offset_y"] != 0 or s["offset_x"] != 0:
            parts.append(f"Y:{s['offset_y']} X:{s['offset_x']}")
        if not s["h_align"]: parts.append("정렬OFF")
        if s["trim_margin_x"]: parts.append("여백X")
        if s["flip_h"]: parts.append("가로반전")
        if s["flip_v"]: parts.append("세로반전")
        if "0도" not in s["rotate_angle"]: parts.append(s["rotate_angle"].split()[0])
        
        if not parts: return "━ [ 기본값 ]"
        return f"━ [ {' | '.join(parts)} ]"

    def setup_ui(self):
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # ==========================================
        # 1. 상단 패널: 보정 및 변환 설정
        # ==========================================
        frame_top = ttk.LabelFrame(main_container, text=" ⚙️ 보정 및 변환 설정 (현재 UI 설정값) ")
        frame_top.pack(side="top", fill="x", pady=(0, 15))

        frame_top_inner = ttk.Frame(frame_top, style="Panel.TFrame")
        frame_top_inner.pack(fill="x", padx=10, pady=10)

        # [1-1] 이미지 변환 구역
        frame_transform = ttk.Frame(frame_top_inner, style="Panel.TFrame")
        frame_transform.pack(side="left", fill="y", padx=(0, 20))

        ttk.Label(frame_transform, text="[ 변환 적용 시점 ]", font=("Malgun Gothic", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        ttk.Radiobutton(frame_transform, text="변환 후 피봇 보정 (추천)", variable=self.transform_order, value="before").grid(row=1, column=0, sticky="w", padx=(0, 15))
        ttk.Radiobutton(frame_transform, text="피봇 보정 후 캔버스 회전", variable=self.transform_order, value="after").grid(row=1, column=1, sticky="w")

        ttk.Label(frame_transform, text="[ 반전 및 회전 ]", font=("Malgun Gothic", 9, "bold")).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 5))
        
        frame_flip_rot = ttk.Frame(frame_transform, style="Panel.TFrame")
        frame_flip_rot.grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame_flip_rot, text="가로 뒤집기", variable=self.flip_h).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(frame_flip_rot, text="세로 뒤집기", variable=self.flip_v).pack(side="left", padx=(0, 15))
        
        ttk.Label(frame_flip_rot, text="회전 각도:").pack(side="left")
        rot_values = ["0도 (회전 없음)", "90도 (시계방향)", "180도", "270도 (시계방향)"]
        cb_rot = ttk.Combobox(frame_flip_rot, textvariable=self.rotate_angle, values=rot_values, state="readonly", width=16)
        cb_rot.pack(side="left", padx=5)

        ttk.Separator(frame_top_inner, orient="vertical").pack(side="left", fill="y", padx=20)

        # [1-2] 피봇 조절 구역
        frame_pivot = ttk.Frame(frame_top_inner, style="Panel.TFrame")
        frame_pivot.pack(side="left", fill="y")

        ttk.Label(frame_pivot, text="[ 피봇 위치 조절 ]", font=("Malgun Gothic", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        
        ttk.Label(frame_pivot, text="세로 오프셋:").grid(row=1, column=0, sticky="w", pady=2)
        sb_y = ttk.Spinbox(frame_pivot, from_=-9999, to=9999, textvariable=self.offset_y, width=8)
        sb_y.grid(row=1, column=1, sticky="w", padx=10, pady=2)

        ttk.Label(frame_pivot, text="가로 오프셋:").grid(row=2, column=0, sticky="w", pady=2)
        sb_x = ttk.Spinbox(frame_pivot, from_=-9999, to=9999, textvariable=self.offset_x, width=8)
        sb_x.grid(row=2, column=1, sticky="w", padx=10, pady=2)

        ttk.Checkbutton(frame_pivot, text="좌우 알파 Bbox 중앙 자동 맞춤", variable=self.h_align).grid(row=1, column=2, sticky="w", padx=(20, 0))
        ttk.Checkbutton(frame_pivot, text="최종 캔버스 좌우 여백 최소화", variable=self.trim_margin_x).grid(row=2, column=2, sticky="w", padx=(20, 0))

        # [1-3] 메인 실행 버튼 구역
        frame_actions = ttk.Frame(frame_top_inner, style="Panel.TFrame")
        frame_actions.pack(side="right", fill="y", padx=(10, 0))
        
        ttk.Label(frame_actions, text="[ 메인 작업 실행 ]", font=("Malgun Gothic", 9, "bold")).pack(side="top", fill="x", pady=(0, 5))
        
        ttk.Button(frame_actions, text="▶ 체크된 파일 일괄 처리 시작", style="Success.TButton", command=self.run_batch).pack(side="top", fill="x", pady=(0, 5))
        ttk.Button(frame_actions, text="🌐 모든 파일에 현재설정 덮어쓰기", style="Primary.TButton", command=self.apply_settings_to_all).pack(side="top", fill="x", pady=(0, 5))
        self.btn_undo = ttk.Button(frame_actions, text="↩ 마지막 작업 되돌리기", command=self.undo_batch)
        self.btn_undo.pack(side="top", fill="x")

        # ==========================================
        # 2. 하단 패널: PanedWindow
        # ==========================================
        self.paned_main = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        self.paned_main.pack(fill="both", expand=True)

        frame_left = ttk.Frame(self.paned_main, style="TFrame")
        self.paned_main.add(frame_left, weight=1)

        # 2-1: 저장 옵션
        lf_save = ttk.LabelFrame(frame_left, text=" 💾 저장 옵션 ")
        lf_save.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(lf_save, text="원본 파일에 덮어쓰기 (!주의)", variable=self.overwrite, command=self.toggle_overwrite).pack(anchor="w", padx=10, pady=(10, 5))
        
        frame_save_mode = ttk.Frame(lf_save, style="Panel.TFrame")
        frame_save_mode.pack(fill="x", padx=10, pady=5)
        self.rb_orig = ttk.Radiobutton(frame_save_mode, text="각 원본 폴더 저장", variable=self.save_mode, value="original", command=self.toggle_save_mode)
        self.rb_orig.pack(side="left", padx=(0, 10))
        self.rb_single = ttk.Radiobutton(frame_save_mode, text="단일 폴더 취합", variable=self.save_mode, value="single", command=self.toggle_save_mode)
        self.rb_single.pack(side="left")

        frame_dir = ttk.Frame(lf_save, style="Panel.TFrame")
        frame_dir.pack(fill="x", padx=10, pady=5)
        self.btn_out_dir = ttk.Button(frame_dir, text="📁 폴더 선택", command=self.select_output_dir)
        self.btn_out_dir.pack(side="left")
        self.lbl_out_dir = ttk.Label(frame_dir, text="[미지정]", style="Muted.TLabel")
        self.lbl_out_dir.pack(side="left", padx=10, fill="x", expand=True)
        
        self.toggle_save_mode() 

        # 2-2: 작업 파일 목록
        lf_list = ttk.LabelFrame(frame_left, text=" 📂 작업 파일 목록 (Ctrl/Shift 다중 선택 지원) ")
        lf_list.pack(fill="both", expand=True, pady=(0, 10))

        self.lbl_input_info = ttk.Label(lf_list, text="체크됨: 0개 / 전체: 0개", font=("Malgun Gothic", 10, "bold"))
        self.lbl_input_info.pack(side="bottom", pady=(5, 10))

        frame_btns = ttk.Frame(lf_list, style="Panel.TFrame")
        frame_btns.pack(side="top", fill="x", padx=10, pady=(10, 5))
        ttk.Button(frame_btns, text="파일/폴더 열기", command=self.load_files_dialog, style="Primary.TButton").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(frame_btns, text="선택 항목 비우기", command=self.clear_list).pack(side="right", fill="x")

        frame_check_btns = ttk.Frame(lf_list, style="Panel.TFrame")
        frame_check_btns.pack(side="top", fill="x", padx=10, pady=(0, 5))
        ttk.Button(frame_check_btns, text="☑ 전체 체크", command=self.check_all).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(frame_check_btns, text="☐ 체크 해제", command=self.uncheck_all).pack(side="right", expand=True, fill="x", padx=(2, 0))

        ttk.Label(lf_list, text="* 더블클릭: 이름 변경 / 클릭: 설정 불러오기", style="Muted.TLabel").pack(side="top", pady=(0, 5))

        frame_list_inner = ttk.Frame(lf_list, style="Panel.TFrame")
        frame_list_inner.pack(side="top", expand=True, fill="both", padx=10, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(frame_list_inner)
        scrollbar.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(frame_list_inner, columns=("check", "name", "settings"), show="headings", yscrollcommand=scrollbar.set, selectmode="extended")
        self.tree.heading("check", text="처리")
        self.tree.column("check", width=40, anchor="center", stretch=False)
        self.tree.heading("name", text="파일 이름", anchor="w")
        self.tree.column("name", width=150, anchor="w", stretch=True)
        self.tree.heading("settings", text="적용된 설정", anchor="w")
        self.tree.column("settings", width=180, anchor="w", stretch=True)
        self.tree.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.tree.yview)

        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click) 

        # 드래그 앤 드롭 인식률 강화를 위해 개별 위젯에도 직접 바인딩
        self.tree.drop_target_register(DND_FILES)
        self.tree.dnd_bind('<<Drop>>', self.on_drop)
        self.paned_main.drop_target_register(DND_FILES)
        self.paned_main.dnd_bind('<<Drop>>', self.on_drop)

        # --- 하단 우측 (실시간 미리보기) ---
        frame_right = ttk.LabelFrame(self.paned_main, text=" 👁️ 실시간 미리보기 (현재 설정 반영) ")
        self.paned_main.add(frame_right, weight=3) 

        frame_right_lbls = ttk.Frame(frame_right, style="Panel.TFrame")
        frame_right_lbls.pack(fill="x", padx=10, pady=(10, 5))
        
        frame_orig_title = ttk.Frame(frame_right_lbls, style="Panel.TFrame")
        frame_orig_title.pack(side="left", expand=True)
        ttk.Label(frame_orig_title, text="[ 원본 캔버스 ]", font=("Malgun Gothic", 10, "bold")).pack(side="top")
        self.lbl_orig_dim = ttk.Label(frame_orig_title, text="(0 x 0 px)", style="Muted.TLabel")
        self.lbl_orig_dim.pack(side="top")

        frame_res_title = ttk.Frame(frame_right_lbls, style="Panel.TFrame")
        frame_res_title.pack(side="left", expand=True)
        ttk.Label(frame_res_title, text="[ 변환 및 보정 완료 ]", font=("Malgun Gothic", 10, "bold")).pack(side="top")
        self.lbl_res_dim = ttk.Label(frame_res_title, text="(0 x 0 px)", style="Muted.TLabel")
        self.lbl_res_dim.pack(side="top")

        self.frame_canvases = ttk.Frame(frame_right, style="Panel.TFrame")
        self.frame_canvases.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        # 캔버스는 초기화 시 빈 객체로 생성, 나중에 apply_theme에서 색상 부여
        self.canvas_orig = tk.Canvas(self.frame_canvases, bd=0, highlightthickness=1, relief="flat")
        self.canvas_orig.pack(side="left", expand=True, fill="both", padx=(0, 5))

        self.canvas_res = tk.Canvas(self.frame_canvases, bd=0, highlightthickness=1, relief="flat")
        self.canvas_res.pack(side="left", expand=True, fill="both", padx=(5, 0))

        self.frame_canvases.bind("<Configure>", self.on_canvas_resize)

    # ------------------ 기능 메서드 ------------------

    def apply_settings_to_all(self):
        if not self.file_data:
            messagebox.showwarning("안내", "목록에 파일이 없습니다.")
            return

        ans = messagebox.askyesno("확인", "현재 설정되어 있는 옵션들을 목록에 있는 모든 파일에 일괄 적용하시겠습니까?\n(각 파일들의 기존 설정값은 덮어씌워집니다)")
        if not ans: return

        current_settings = self.get_current_ui_settings()
        
        for f in self.file_data:
            f["settings"] = current_settings.copy()
            self._update_tree_item(f)
            
        self.update_preview()
        messagebox.showinfo("완료", "모든 파일에 설정이 일괄 덮어씌워졌습니다.")

    def on_ui_change(self, event=None):
        if not self._is_updating_ui:
            selected_items = self.tree.selection()
            if selected_items:
                current_settings = self.get_current_ui_settings()
                
                for item_id in selected_items:
                    for f in self.file_data:
                        if f["id"] == item_id:
                            f["settings"] = current_settings.copy()
                            self._update_tree_item(f)
                            break
                            
            self.update_preview()

    def on_canvas_resize(self, event):
        if str(event.widget) == str(self.frame_canvases):
            if self._resize_timer:
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(200, self.update_preview)

    def draw_checkerboard(self, canvas, width, height, size=10):
        canvas.delete("checkerboard")
        is_dark = self.is_dark_mode.get()
        color1 = "#ffffff" if not is_dark else "#2A2A2A"
        color2 = "#f1f5f9" if not is_dark else "#202020"
        
        for y in range(0, height, size):
            for x in range(0, width, size):
                color = color1 if ((x//size) + (y//size)) % 2 == 0 else color2
                canvas.create_rectangle(x, y, x+size, y+size, fill=color, outline="", tags="checkerboard")
        canvas.tag_lower("checkerboard")

    def toggle_overwrite(self):
        if self.overwrite.get():
            self.rb_orig.state(['disabled'])
            self.rb_single.state(['disabled'])
            self.btn_out_dir.state(['disabled'])
            self.btn_undo.state(['disabled'])
            self.lbl_out_dir.config(text="원본 파일에 덮어씁니다.\n되돌릴 수 없으니 주의하세요!")
        else:
            self.rb_orig.state(['!disabled'])
            self.rb_single.state(['!disabled'])
            self.btn_undo.state(['!disabled'])
            self.toggle_save_mode()

    def toggle_save_mode(self):
        if not self.overwrite.get():
            if self.save_mode.get() == "single":
                self.btn_out_dir.state(['!disabled'])
                if self.output_dir:
                    self.lbl_out_dir.config(text=self.output_dir)
                else:
                    self.lbl_out_dir.config(text="[폴더 미지정]")
            else:
                self.btn_out_dir.state(['disabled'])
                self.lbl_out_dir.config(text="기본값: 원본 폴더에 '_pivotfix' 추가")

    def update_selection_info(self):
        checked_count = sum(1 for f in self.file_data if f["checked"])
        total_count = len(self.file_data)
        self.lbl_input_info.config(text=f"체크됨: {checked_count}개 / 전체: {total_count}개")

    def load_files_dialog(self):
        paths = filedialog.askopenfilenames(filetypes=[("PNG Files", "*.png")])
        if paths:
            self.add_paths_to_list(paths)

    def on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        if not paths: return
        
        png_files = []
        for p in paths:
            if os.path.isdir(p):
                png_files.extend(glob.glob(os.path.join(p, "*.png")))
            elif p.lower().endswith(".png"):
                png_files.append(p)
                
        if png_files:
            self.add_paths_to_list(png_files)
        else:
            messagebox.showwarning("안내", "PNG 파일이 발견되지 않았습니다.")

    def add_paths_to_list(self, new_paths):
        first_new_id = None
        current_settings = self.get_current_ui_settings()

        for p in new_paths:
            p_norm = os.path.normpath(p)
            if not any(f["path"] == p_norm for f in self.file_data):
                name = os.path.basename(p_norm)
                item_id = self.tree.insert("", tk.END, values=("☑", name, ""))
                
                f_data = {
                    "id": item_id, 
                    "path": p_norm, 
                    "name": name, 
                    "checked": True,
                    "settings": current_settings.copy()
                }
                self.file_data.append(f_data)
                self._update_tree_item(f_data)
                
                if first_new_id is None:
                    first_new_id = item_id
                
        self.update_selection_info()
        
        if first_new_id and not self.preview_path:
            self.tree.selection_set(first_new_id)
            self.tree.focus(first_new_id)

    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell" and column == "#1":
            item_id = self.tree.identify_row(event.y)
            if item_id:
                for f in self.file_data:
                    if f["id"] == item_id:
                        f["checked"] = not f["checked"]
                        self._update_tree_item(f)
                        self.update_selection_info()
                        break

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if len(selection) == 1:
            item_id = selection[0]
            for f in self.file_data:
                if f["id"] == item_id:
                    self._is_updating_ui = True 
                    try:
                        s = f["settings"]
                        
                        self.offset_y.set(str(s["offset_y"]))
                        self.offset_x.set(str(s["offset_x"]))
                        self.h_align.set(s["h_align"])
                        self.trim_margin_x.set(s["trim_margin_x"])
                        self.flip_h.set(s["flip_h"])
                        self.flip_v.set(s["flip_v"])
                        self.rotate_angle.set(s["rotate_angle"])
                        self.transform_order.set(s["transform_order"])
                        
                        self.preview_path = f["path"]
                    finally:
                        self._is_updating_ui = False
                    
                    self.update_preview()
                    break

    def on_tree_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell" and column == "#2":
            item_id = self.tree.identify_row(event.y)
            if not item_id: return
            
            target_f = None
            for f in self.file_data:
                if f["id"] == item_id:
                    target_f = f
                    break
                    
            if not target_f: return
            
            old_name = target_f["name"]
            
            new_name = simpledialog.askstring("이름 변경", "저장될 새 파일 이름을 입력하세요:", initialvalue=old_name, parent=self.root)
            
            if new_name and new_name != old_name:
                if not new_name.lower().endswith(".png"):
                    new_name += ".png"
                    
                target_f["name"] = new_name
                self._update_tree_item(target_f)

    def check_all(self):
        for f in self.file_data:
            if not f["checked"]:
                f["checked"] = True
                self._update_tree_item(f)
        self.update_selection_info()

    def uncheck_all(self):
        for f in self.file_data:
            if f["checked"]:
                f["checked"] = False
                self._update_tree_item(f)
        self.update_selection_info()

    def clear_list(self):
        checked_files = [f for f in self.file_data if f["checked"]]
        
        if checked_files:
            for f in checked_files:
                self.tree.delete(f["id"])
                
            self.file_data = [f for f in self.file_data if not f["checked"]]
            
            if not any(f["path"] == self.preview_path for f in self.file_data):
                self.preview_path = None
                self.canvas_orig.delete("all")
                self.canvas_res.delete("all")
                self.lbl_orig_dim.config(text="(0 x 0 px)")
                self.lbl_res_dim.config(text="(0 x 0 px)")
            
            self.update_selection_info()
            return
            
        ans = messagebox.askyesno("안내", "체크된(☑) 파일이 없습니다.\n목록 전체를 비우시겠습니까?")
        if ans:
            self.file_data.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.preview_path = None
            self.update_selection_info()
            self.canvas_orig.delete("all")
            self.canvas_res.delete("all")
            self.lbl_orig_dim.config(text="(0 x 0 px)")
            self.lbl_res_dim.config(text="(0 x 0 px)")

    def select_output_dir(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_dir = folder_path
            self.save_mode.set("single")
            self.toggle_save_mode()

    def get_alpha_bbox(self, img):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img.split()[-1].getbbox()

    def apply_transformations(self, img, flip_h, flip_v, rot_val):
        if flip_h:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if flip_v:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
        if "90도" in rot_val:
            img = img.transpose(Image.ROTATE_270)
        elif "180도" in rot_val:
            img = img.transpose(Image.ROTATE_180)
        elif "270도" in rot_val:
            img = img.transpose(Image.ROTATE_90)
            
        return img

    def process_image(self, img, s):
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if s["transform_order"] == "before":
            img = self.apply_transformations(img, s["flip_h"], s["flip_v"], s["rotate_angle"])
            
        W, H = img.size
        bbox = self.get_alpha_bbox(img)
        
        if bbox is None:
            left, upper, right, lower = 0, 0, W, H
            crop_img = img.copy()
        else:
            left, upper, right, lower = bbox
            crop_img = img.crop(bbox)

        cW, cH = crop_img.size

        if s["h_align"]:
            rel_x = -(cW // 2) + s["offset_x"]
        else:
            rel_x = left - (W // 2) + s["offset_x"]

        rel_y = -cH - s["offset_y"]

        need_left = max(0, -rel_x)
        need_right = max(0, rel_x + cW)
        need_top = max(0, -rel_y)
        need_bottom = max(0, rel_y + cH)

        if not s.get("trim_margin_x", False):
            # 기본 모드: 정사각형 캔버스 강제
            half_size = max(need_left, need_right, need_top, need_bottom)
            nW = half_size * 2
            nH = half_size * 2
        else:
            # 여백 최소화 모드: 세로는 안정 높이 유지, 가로는 필요한 만큼만 할당 (직사각형 가능)
            half_h = max(need_left, need_right, need_top, need_bottom)
            half_w = max(need_left, need_right)
            nW = half_w * 2
            nH = half_h * 2

        nW = max(nW, 2)
        nH = max(nH, 2)

        if nW % 2 != 0:
            nW += 1
        if nH % 2 != 0:
            nH += 1

        pivot_x = nW // 2
        pivot_y = nH // 2

        paste_x = pivot_x + rel_x
        paste_y = pivot_y + rel_y

        new_img = Image.new("RGBA", (nW, nH), (0, 0, 0, 0))
        new_img.paste(crop_img, (paste_x, paste_y))

        if s["transform_order"] == "after":
            new_img = self.apply_transformations(new_img, s["flip_h"], s["flip_v"], s["rotate_angle"])

        return new_img

    def resize_for_preview(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        if ratio >= 1: ratio = int(ratio)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        return img.resize((new_w, new_h), Image.Resampling.NEAREST)

    def update_preview(self):
        self.canvas_orig.delete("all")
        self.canvas_res.delete("all")
        
        c_w = self.canvas_orig.winfo_width()
        c_h = self.canvas_orig.winfo_height()
        
        if c_w <= 1 or c_h <= 1: return

        self.draw_checkerboard(self.canvas_orig, c_w, c_h)
        self.draw_checkerboard(self.canvas_res, c_w, c_h)

        if not self.preview_path or not os.path.exists(self.preview_path):
            return

        try:
            img = Image.open(self.preview_path).convert("RGBA")
            
            current_settings = self.get_current_ui_settings()
            res_img = self.process_image(img, current_settings)

            self.lbl_orig_dim.config(text=f"({img.width} x {img.height} px)")
            self.lbl_res_dim.config(text=f"({res_img.width} x {res_img.height} px)")

            safe_w = c_w - 40
            safe_h = c_h - 40
            if safe_w < 10 or safe_h < 10: return
            
            cx = c_w // 2
            cy = c_h // 2

            img_preview = self.resize_for_preview(img, safe_w, safe_h)
            self.tk_orig = ImageTk.PhotoImage(img_preview)
            self.canvas_orig.create_image(cx, cy, image=self.tk_orig, anchor="center", tags="preview_image")

            orig_w, orig_h = img_preview.width, img_preview.height
            orig_x1 = cx - (orig_w // 2)
            orig_y1 = cy - (orig_h // 2)
            orig_x2 = orig_x1 + orig_w
            orig_y2 = orig_y1 + orig_h
            outline_color = "#ef4444" if not self.is_dark_mode.get() else "#F87171"
            self.canvas_orig.create_rectangle(orig_x1, orig_y1, orig_x2, orig_y2, outline=outline_color, dash=(2, 2), tags="preview_image")

            res_preview = self.resize_for_preview(res_img, safe_w, safe_h)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(cx, cy, image=self.tk_res, anchor="center", tags="preview_image")

            res_w, res_h = res_preview.width, res_preview.height
            res_x1 = cx - (res_w // 2)
            res_y1 = cy - (res_h // 2)
            res_x2 = res_x1 + res_w
            res_y2 = res_y1 + res_h
            self.canvas_res.create_rectangle(res_x1, res_y1, res_x2, res_y2, outline=outline_color, dash=(2, 2), tags="preview_image")

            cross_color = "#06b6d4" if not self.is_dark_mode.get() else "#22D3EE"
            self.canvas_res.create_line(0, cy, c_w, cy, fill=cross_color, width=1, tags="crosshair")
            self.canvas_res.create_line(cx, 0, cx, c_h, fill=cross_color, width=1, tags="crosshair")
            
        except Exception as e:
            print(f"미리보기 업데이트 실패: {e}")

    def images_are_identical(self, img_a, img_b):
        if img_a.size != img_b.size:
            return False
        if img_a.mode != "RGBA":
            img_a = img_a.convert("RGBA")
        if img_b.mode != "RGBA":
            img_b = img_b.convert("RGBA")
            
        diff = ImageChops.difference(img_a, img_b)
        return diff.getbbox() is None

    def get_unique_backup_path(self, backup_dir, filename):
        name, ext = os.path.splitext(filename)
        base_path = os.path.join(backup_dir, filename)
        if not os.path.exists(base_path):
            return base_path
        
        counter = 1
        while True:
            new_name = f"{name}_{counter:03d}{ext}"
            new_path = os.path.join(backup_dir, new_name)
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def backup_original_file(self, orig_path):
        backup_dir = os.path.join(os.path.dirname(orig_path), "_pivotfix_backup")
        os.makedirs(backup_dir, exist_ok=True)
        filename = os.path.basename(orig_path)
        backup_path = self.get_unique_backup_path(backup_dir, filename)
        shutil.copy2(orig_path, backup_path)
        return backup_path

    def open_folder(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("오류", f"폴더 열기 실패:\n{e}")

    def show_batch_result_log(self, total_count, success_count, skipped_count, failure_logs, skipped_logs, output_dirs, mode_text):
        log_win = tk.Toplevel(self.root)
        log_win.title("처리 결과 보고서")
        log_win.geometry("560x520")
        log_win.minsize(520, 460)
        if self.is_always_on_top.get():
            log_win.attributes('-topmost', True)
        
        c = self.get_colors()
        log_win.configure(bg=c["BG_COLOR"])
        
        main_frame = ttk.Frame(log_win, style="TFrame")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        
        lbl_title = ttk.Label(main_frame, text="[ 작업 처리 완료 ]", font=("Malgun Gothic", 11, "bold"), foreground=c["PRIMARY_COLOR"])
        lbl_title.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        fail_count = len(failure_logs)
        
        summary_frame = ttk.Frame(main_frame, style="Panel.TFrame")
        summary_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(summary_frame, text=f"• 전체 대상 파일: {total_count}개").pack(anchor="w", padx=10, pady=2)
        ttk.Label(summary_frame, text=f"• 성공: {success_count}개", foreground=c["SUCCESS_COLOR"], font=("Malgun Gothic", 10, "bold")).pack(anchor="w", padx=10, pady=2)
        ttk.Label(summary_frame, text=f"• 변경 없음 / 건너뜀: {skipped_count}개").pack(anchor="w", padx=10, pady=2)
        ttk.Label(summary_frame, text=f"• 실패: {fail_count}개", foreground=c["DANGER_COLOR"] if fail_count > 0 else c["TEXT_COLOR"]).pack(anchor="w", padx=10, pady=2)
        ttk.Label(summary_frame, text=f"• 저장 방식: {mode_text}").pack(anchor="w", padx=10, pady=2)

        if failure_logs or skipped_logs:
            detail_frame = ttk.LabelFrame(main_frame, text=" ⚠️ 세부 내역 ")
            detail_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
            
            scrollbar = ttk.Scrollbar(detail_frame)
            scrollbar.pack(side="right", fill="y")
            
            txt = tk.Text(detail_frame, font=("Malgun Gothic", 9), bg=c["PANEL_BG"], fg=c["TEXT_COLOR"], wrap="word", borderwidth=0, yscrollcommand=scrollbar.set)
            txt.pack(side="left", expand=True, fill="both", padx=10, pady=10)
            scrollbar.config(command=txt.yview)
            
            if failure_logs:
                txt.insert("end", "[ 실패 목록 ]\n")
                for i, log in enumerate(failure_logs):
                    if i >= 10:
                        txt.insert("end", f"... 외 {fail_count - 10}개 실패\n")
                        break
                    txt.insert("end", f"- {os.path.basename(log['file'])}: {log['reason']}\n")
                txt.insert("end", "\n")
                
            if skipped_logs:
                txt.insert("end", "[ 변경 없음 / 건너뜀 목록 ]\n")
                for i, log in enumerate(skipped_logs):
                    if i >= 10:
                        txt.insert("end", f"... 외 {skipped_count - 10}개 건너뜀\n")
                        break
                    txt.insert("end", f"- {os.path.basename(log)}\n")
                    
            txt.config(state="disabled")
        else:
            empty_frame = ttk.Frame(main_frame, style="TFrame")
            empty_frame.grid(row=2, column=0, sticky="nsew")

        btn_frame = ttk.Frame(main_frame, style="TFrame")
        btn_frame.grid(row=3, column=0, sticky="ew")
        
        btn_frame.columnconfigure(0, weight=1)
        
        if output_dirs:
            if len(output_dirs) > 1:
                ttk.Label(btn_frame, text=f"(*저장 폴더 {len(output_dirs)}곳)").grid(row=0, column=0, sticky="w")
            target_dir = list(output_dirs)[0]
            btn_open = ttk.Button(btn_frame, text="결과 폴더 열기", command=lambda d=target_dir: self.open_folder(d), style="Primary.TButton")
            btn_open.grid(row=0, column=1, sticky="e", padx=(0, 5))
            
        btn_close = ttk.Button(btn_frame, text="닫기", command=log_win.destroy)
        btn_close.grid(row=0, column=2, sticky="e")

    def run_batch(self):
        target_files = [f for f in self.file_data if f["checked"]]
        
        if not target_files:
            messagebox.showwarning("안내", "체크된(☑) 파일이 없습니다.\n처리할 파일을 목록에서 체크해주세요.")
            return

        is_overwrite = self.overwrite.get()
        save_mode_val = self.save_mode.get()
        
        if is_overwrite:
            ans = messagebox.askyesno("경고", f"체크된 {len(target_files)}개 원본 파일 자체를 덮어씁니다.\n이 작업은 되돌리기로 복구할 수 없습니다.\n(진행 전 _pivotfix_backup 폴더에 자동 백업됩니다.)\n\n정말로 진행하시겠습니까?")
            if not ans: return
        elif save_mode_val == "single" and not self.output_dir:
            messagebox.showwarning("안내", "단일 폴더 저장 모드가 선택되었지만, 저장할 폴더가 지정되지 않았습니다.\n폴더를 먼저 선택해주세요.")
            return

        success_count = 0
        skipped_count = 0
        failure_logs = []
        skipped_logs = []
        output_dirs = set()
        
        if is_overwrite:
            mode_text = "원본 파일 덮어쓰기 (자동 백업 완료)"
        elif save_mode_val == "single":
            mode_text = "단일 폴더 취합"
        else:
            mode_text = "각 원본 폴더 저장"

        self.last_generated_files.clear()

        for idx, file_info in enumerate(target_files):
            orig_path = file_info["path"]
            target_name = file_info["name"]
            orig_name = os.path.basename(orig_path)
            
            s = file_info["settings"]

            try:
                img = Image.open(orig_path)
                res_img = self.process_image(img, s)
                
                if self.images_are_identical(img, res_img) and target_name == orig_name:
                    skipped_count += 1
                    skipped_logs.append(orig_path)
                    img.close()
                    continue

                if is_overwrite:
                    try:
                        self.backup_original_file(orig_path)
                    except Exception as e:
                        img.close()
                        raise Exception(f"백업 실패: {e}")

                img.close() 
                
                if is_overwrite:
                    save_dir = os.path.dirname(orig_path)
                    save_path = os.path.join(save_dir, target_name)
                    res_img.save(save_path, "PNG")
                    
                    if target_name != orig_name and orig_path != save_path:
                        if os.path.exists(orig_path):
                            try:
                                os.remove(orig_path)
                            except Exception as e:
                                print(f"이전 원본 파일 삭제 실패: {e}")
                    
                    file_info["path"] = save_path
                    if self.preview_path == orig_path:
                        self.preview_path = save_path
                    output_dirs.add(save_dir)
                else:
                    if save_mode_val == "single":
                        save_dir = self.output_dir
                    else: 
                        save_dir = os.path.dirname(orig_path)
                    
                    if target_name == orig_name:
                        name, ext = os.path.splitext(target_name)
                        final_filename = f"{name}_pivotfix.png"
                    else:
                        final_filename = target_name
                        
                    save_path = os.path.join(save_dir, final_filename)
                    self.last_generated_files.append(save_path) 
                    res_img.save(save_path, "PNG")
                    output_dirs.add(save_dir)
                
                success_count += 1
            except Exception as e:
                failure_logs.append({"file": orig_path, "reason": str(e)})
                print(f"파일 처리 실패 ({orig_path}): {e}")
                
            if idx % 10 == 0:
                self.root.update()

        self.show_batch_result_log(len(target_files), success_count, skipped_count, failure_logs, skipped_logs, output_dirs, mode_text)

    def undo_batch(self):
        if self.overwrite.get():
            messagebox.showwarning("경고", "덮어쓰기 모드에서는 파일 삭제(되돌리기) 기능을 사용할 수 없습니다.")
            return
            
        if not self.last_generated_files:
            messagebox.showinfo("안내", "되돌릴 작업 내역이 없습니다.")
            return
            
        confirm = messagebox.askyesno("되돌리기 확인", f"방금 생성된 {len(self.last_generated_files)}개의 _pivotfix.png 파일을 삭제하시겠습니까?")
        if not confirm: return
        
        count = 0
        for path in self.last_generated_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    count += 1
                except Exception as e:
                    print(f"삭제 실패 ({path}): {e}")
                    
        self.last_generated_files.clear()
        messagebox.showinfo("되돌리기 완료", f"{count}개의 파일이 안전하게 삭제되었습니다. 🗑️")

if __name__ == "__main__":
    try:
        root = TkinterDnD.Tk()
    except Exception as e:
        print("tkinterdnd2 초기화 오류:", e)
        root = tk.Tk()
        
    app = PivotFixerApp(root)
    root.mainloop()