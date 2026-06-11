import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk

# 전체 컬러 팔레트 (Modern UI 감성)
BG_COLOR = "#F0F2F5"       
PANEL_BG = "#FFFFFF"       
PRIMARY_COLOR = "#4F46E5"  
PRIMARY_HOVER = "#4338CA"  
SUCCESS_COLOR = "#10B981"  
SUCCESS_HOVER = "#059669"  
DANGER_COLOR = "#EF4444"   
TEXT_COLOR = "#1E293B"     
TEXT_MUTED = "#64748B"     
BORDER_COLOR = "#E2E8F0"   

class PivotFixerApp:
    def __init__(self, root):
        self.root = root
        self.version = "v0.1.6"
        self.root.title(f"PNG 피봇 보정 툴 (Pixel Art Optimizer) - {self.version}")

        self.root.geometry("1400x850")
        self.root.minsize(1200, 750)
        self.root.resizable(True, True)
        self.root.configure(bg=BG_COLOR)

        self.setup_styles()

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        # 파일 데이터 구조 확장: 개별 설정값 보관
        # {"id": id, "path": path, "name": name, "checked": bool, "settings": dict}
        self.file_data = []
        self.preview_path = None
        self.output_dir = ""
        self.last_generated_files = [] 

        # 현재 UI 컨트롤에 보여지는 설정 변수들
        self.offset_y = tk.IntVar(value=0)
        self.offset_x = tk.IntVar(value=0)
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
        
        # 파일 클릭 시 UI 연동으로 인한 무한 루프 방지 플래그
        self._is_updating_ui = False

        self.setup_ui()

    def get_current_ui_settings(self):
        """현재 UI에 입력된 설정값을 딕셔너리로 반환"""
        return {
            "offset_y": self.offset_y.get(),
            "offset_x": self.offset_x.get(),
            "h_align": self.h_align.get(),
            "trim_margin_x": self.trim_margin_x.get(),
            "flip_h": self.flip_h.get(),
            "flip_v": self.flip_v.get(),
            "rotate_angle": self.rotate_angle.get(),
            "transform_order": self.transform_order.get()
        }

    def format_settings_summary(self, s):
        """설정 딕셔너리를 한눈에 보기 쉬운 짧은 텍스트로 요약"""
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

    def _update_tree_item(self, f):
        """파일 정보 딕셔너리 f를 바탕으로 Treeview의 행(체크여부, 이름, 요약텍스트, 색상)을 일괄 갱신합니다."""
        check_str = "☑" if f["checked"] else "☐"
        summary = self.format_settings_summary(f["settings"])
        # 설정이 기본값이 아니면 'modified' 태그를 부여하여 붉고 굵은 글씨로 표시
        tag = "modified" if summary != "━ [ 기본값 ]" else "default"
        self.tree.item(f["id"], values=(check_str, f["name"], summary), tags=(tag,))

    def setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        default_font = ("Malgun Gothic", 10)
        bold_font = ("Malgun Gothic", 10, "bold")
        title_font = ("Malgun Gothic", 11, "bold")

        style.configure(".", font=default_font, background=BG_COLOR, foreground=TEXT_COLOR)

        style.configure("TFrame", background=BG_COLOR)
        style.configure("Panel.TFrame", background=PANEL_BG)

        style.configure("TLabelframe", background=PANEL_BG, borderwidth=1, bordercolor=BORDER_COLOR, relief="flat")
        style.configure("TLabelframe.Label", background=PANEL_BG, foreground=PRIMARY_COLOR, font=title_font, padding=(10, 5))

        style.configure("TLabel", background=PANEL_BG, foreground=TEXT_COLOR, font=default_font)
        style.configure("Muted.TLabel", foreground=TEXT_MUTED, font=("Malgun Gothic", 9))
        style.configure("Danger.TLabel", foreground=DANGER_COLOR, font=bold_font)
        style.configure("Success.TLabel", foreground=SUCCESS_COLOR, font=bold_font)

        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT_COLOR, font=default_font, indicatorsize=16)
        style.map("TCheckbutton", background=[("active", PANEL_BG)])

        style.configure("TRadiobutton", background=PANEL_BG, foreground=TEXT_COLOR, font=default_font, indicatorsize=16)
        style.map("TRadiobutton", background=[("active", PANEL_BG)])

        style.configure("TCombobox", padding=5, font=default_font, bordercolor=BORDER_COLOR)

        style.configure("TButton", font=default_font, padding=(10, 5), background="#F8FAFC", borderwidth=1, bordercolor=BORDER_COLOR, relief="flat")
        style.map("TButton", background=[("active", "#E2E8F0")], bordercolor=[("active", "#CBD5E1")])

        style.configure("Primary.TButton", font=bold_font, padding=(10, 5), background=PRIMARY_COLOR, foreground="white", borderwidth=0, relief="flat")
        style.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])

        style.configure("Success.TButton", font=("Malgun Gothic", 12, "bold"), padding=(10, 8), background=SUCCESS_COLOR, foreground="white", borderwidth=0, relief="flat")
        style.map("Success.TButton", background=[("active", SUCCESS_HOVER)])

        style.configure("Treeview", font=default_font, rowheight=30, background="#FFFFFF", fieldbackground="#FFFFFF", borderwidth=0)
        style.configure("Treeview.Heading", font=bold_font, background="#F8FAFC", foreground=TEXT_COLOR, borderwidth=1, bordercolor=BORDER_COLOR, padding=5)
        style.map("Treeview", background=[('selected', "#EEF2FF")], foreground=[('selected', PRIMARY_COLOR)])
        
        style.configure("TScrollbar", background="#CBD5E1", troughcolor="#F8FAFC", borderwidth=0, arrowsize=12, relief="flat")
        style.map("TScrollbar", background=[("active", "#94A3B8")])

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

        ttk.Label(frame_transform, text="[ 변환 적용 시점 ]", font=("Malgun Gothic", 9, "bold"), foreground=PRIMARY_COLOR).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        ttk.Radiobutton(frame_transform, text="변환 후 피봇 보정 (추천)", variable=self.transform_order, value="before", command=self.on_ui_change).grid(row=1, column=0, sticky="w", padx=(0, 15))
        ttk.Radiobutton(frame_transform, text="피봇 보정 후 캔버스 회전", variable=self.transform_order, value="after", command=self.on_ui_change).grid(row=1, column=1, sticky="w")

        ttk.Label(frame_transform, text="[ 반전 및 회전 ]", font=("Malgun Gothic", 9, "bold"), foreground=PRIMARY_COLOR).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 5))
        
        frame_flip_rot = ttk.Frame(frame_transform, style="Panel.TFrame")
        frame_flip_rot.grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame_flip_rot, text="가로 뒤집기", variable=self.flip_h, command=self.on_ui_change).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(frame_flip_rot, text="세로 뒤집기", variable=self.flip_v, command=self.on_ui_change).pack(side="left", padx=(0, 15))
        
        ttk.Label(frame_flip_rot, text="회전 각도:").pack(side="left")
        rot_values = ["0도 (회전 없음)", "90도 (시계방향)", "180도", "270도 (시계방향)"]
        cb_rot = ttk.Combobox(frame_flip_rot, textvariable=self.rotate_angle, values=rot_values, state="readonly", width=16)
        cb_rot.pack(side="left", padx=5)
        cb_rot.bind("<<ComboboxSelected>>", lambda e: self.on_ui_change())

        ttk.Separator(frame_top_inner, orient="vertical").pack(side="left", fill="y", padx=20)

        # [1-2] 피봇 조절 구역
        frame_pivot = ttk.Frame(frame_top_inner, style="Panel.TFrame")
        frame_pivot.pack(side="left", fill="y")

        ttk.Label(frame_pivot, text="[ 피봇 위치 조절 ]", font=("Malgun Gothic", 9, "bold"), foreground=PRIMARY_COLOR).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        
        offset_values = list(range(-10, 11))
        ttk.Label(frame_pivot, text="세로 오프셋:").grid(row=1, column=0, sticky="w", pady=2)
        cb_y = ttk.Combobox(frame_pivot, textvariable=self.offset_y, values=offset_values, state="readonly", width=5)
        cb_y.grid(row=1, column=1, sticky="w", padx=10, pady=2)
        cb_y.bind("<<ComboboxSelected>>", lambda e: self.on_ui_change())

        ttk.Label(frame_pivot, text="가로 오프셋:").grid(row=2, column=0, sticky="w", pady=2)
        cb_x = ttk.Combobox(frame_pivot, textvariable=self.offset_x, values=offset_values, state="readonly", width=5)
        cb_x.grid(row=2, column=1, sticky="w", padx=10, pady=2)
        cb_x.bind("<<ComboboxSelected>>", lambda e: self.on_ui_change())

        ttk.Checkbutton(frame_pivot, text="좌우 알파 Bbox 중앙 자동 맞춤", variable=self.h_align, command=self.on_ui_change).grid(row=1, column=2, sticky="w", padx=(20, 0))
        ttk.Checkbutton(frame_pivot, text="최종 캔버스 좌우 여백 최소화", variable=self.trim_margin_x, command=self.on_ui_change).grid(row=2, column=2, sticky="w", padx=(20, 0))

        # [1-3] 메인 실행 버튼 구역 (최우측 상단)
        frame_actions = ttk.Frame(frame_top_inner, style="Panel.TFrame")
        frame_actions.pack(side="right", fill="y", padx=(10, 0))
        
        ttk.Label(frame_actions, text="[ 메인 작업 실행 ]", font=("Malgun Gothic", 9, "bold"), foreground=PRIMARY_COLOR).pack(side="top", fill="x", pady=(0, 5))
        
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

        frame_btns = ttk.Frame(lf_list, style="Panel.TFrame")
        frame_btns.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Button(frame_btns, text="파일/폴더 열기", command=self.load_files_dialog, style="Primary.TButton").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(frame_btns, text="선택 항목 비우기", command=self.clear_list).pack(side="right", fill="x")

        frame_check_btns = ttk.Frame(lf_list, style="Panel.TFrame")
        frame_check_btns.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Button(frame_check_btns, text="☑ 전체 체크", command=self.check_all).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(frame_check_btns, text="☐ 체크 해제", command=self.uncheck_all).pack(side="right", expand=True, fill="x", padx=(2, 0))

        ttk.Label(lf_list, text="* 더블클릭: 이름 변경 / 클릭: 설정 불러오기", style="Muted.TLabel").pack(pady=(0, 5))

        frame_list_inner = ttk.Frame(lf_list, style="Panel.TFrame")
        frame_list_inner.pack(expand=True, fill="both", padx=10, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(frame_list_inner)
        scrollbar.pack(side="right", fill="y")
        
        # 다중 선택(extended 모드) 지원 및 설정 요약(settings) 열 추가
        self.tree = ttk.Treeview(frame_list_inner, columns=("check", "name", "settings"), show="headings", yscrollcommand=scrollbar.set, selectmode="extended")
        self.tree.heading("check", text="처리")
        self.tree.column("check", width=40, anchor="center", stretch=False)
        self.tree.heading("name", text="파일 이름", anchor="w")
        self.tree.column("name", width=150, anchor="w", stretch=True)
        self.tree.heading("settings", text="적용된 설정", anchor="w")
        self.tree.column("settings", width=180, anchor="w", stretch=True)
        self.tree.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.tree.yview)

        # 트리뷰 태그 설정 (변경된 설정값을 붉고 굵은 글씨로 강조)
        self.tree.tag_configure("modified", foreground=DANGER_COLOR, font=("Malgun Gothic", 10, "bold"))
        self.tree.tag_configure("default", foreground=TEXT_COLOR, font=("Malgun Gothic", 10))
        
        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)

        self.lbl_input_info = ttk.Label(lf_list, text="체크됨: 0개 / 전체: 0개", font=("Malgun Gothic", 10, "bold"), foreground=PRIMARY_COLOR)
        self.lbl_input_info.pack(pady=(5, 10)) 

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
        ttk.Label(frame_res_title, text="[ 변환 및 보정 완료 ]", font=("Malgun Gothic", 10, "bold"), foreground=PRIMARY_COLOR).pack(side="top")
        self.lbl_res_dim = ttk.Label(frame_res_title, text="(0 x 0 px)", style="Muted.TLabel")
        self.lbl_res_dim.pack(side="top")

        self.frame_canvases = ttk.Frame(frame_right, style="Panel.TFrame")
        self.frame_canvases.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        canvas_bg = "#ffffff"
        
        self.canvas_orig = tk.Canvas(self.frame_canvases, bg=canvas_bg, bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR, relief="flat")
        self.canvas_orig.pack(side="left", expand=True, fill="both", padx=(0, 5))

        self.canvas_res = tk.Canvas(self.frame_canvases, bg=canvas_bg, bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR, relief="flat")
        self.canvas_res.pack(side="left", expand=True, fill="both", padx=(5, 0))

        self.frame_canvases.bind("<Configure>", self.on_canvas_resize)

    # ------------------ 기능 메서드 ------------------

    def apply_settings_to_all(self):
        """현재 UI의 설정을 목록에 있는 모든 파일의 설정에 일괄 덮어씌웁니다."""
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
        """UI 설정값이 변경되었을 때, 선택된 파일들에 즉시 설정을 덮어씌우고(자동 저장) 미리보기를 갱신합니다."""
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
        for y in range(0, height, size):
            for x in range(0, width, size):
                color = "#ffffff" if ((x//size) + (y//size)) % 2 == 0 else "#f1f5f9"
                canvas.create_rectangle(x, y, x+size, y+size, fill=color, outline="", tags="checkerboard")
        canvas.tag_lower("checkerboard")

    def toggle_overwrite(self):
        if self.overwrite.get():
            self.rb_orig.state(['disabled'])
            self.rb_single.state(['disabled'])
            self.btn_out_dir.state(['disabled'])
            self.btn_undo.state(['disabled'])
            self.lbl_out_dir.config(text="원본 파일에 덮어씁니다.\n되돌릴 수 없으니 주의하세요!", foreground=DANGER_COLOR)
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
                    self.lbl_out_dir.config(text=self.output_dir, foreground=PRIMARY_COLOR)
                else:
                    self.lbl_out_dir.config(text="[폴더 미지정]", foreground=TEXT_MUTED)
            else:
                self.btn_out_dir.state(['disabled'])
                self.lbl_out_dir.config(text="기본값: 원본 폴더에 '_pivotfix' 추가", foreground=TEXT_MUTED)

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
        """항목 선택 시, 단일 선택이면 해당 파일의 설정을 UI로 불러옵니다."""
        selection = self.tree.selection()
        if len(selection) == 1:
            item_id = selection[0]
            for f in self.file_data:
                if f["id"] == item_id:
                    self._is_updating_ui = True 
                    s = f["settings"]
                    
                    self.offset_y.set(s["offset_y"])
                    self.offset_x.set(s["offset_x"])
                    self.h_align.set(s["h_align"])
                    self.trim_margin_x.set(s["trim_margin_x"])
                    self.flip_h.set(s["flip_h"])
                    self.flip_v.set(s["flip_v"])
                    self.rotate_angle.set(s["rotate_angle"])
                    self.transform_order.set(s["transform_order"])
                    
                    self.preview_path = f["path"]
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
            self.lbl_out_dir.config(text=folder_path, foreground=PRIMARY_COLOR)
            self.save_mode.set("single")

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
        """개별 파일 설정(s) 딕셔너리를 입력받아 보정을 수행합니다."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if s["transform_order"] == "before":
            img = self.apply_transformations(img, s["flip_h"], s["flip_v"], s["rotate_angle"])
            
        W, H = img.size
        bbox = self.get_alpha_bbox(img)
        
        if bbox is None:
            left, upper, right, lower = 0, 0, W, H
        else:
            left, upper, right, lower = bbox

        if s["h_align"]:
            cx_visible = (left + right) // 2
            rel_x = -cx_visible + s["offset_x"]
        else:
            rel_x = -(W // 2) + s["offset_x"]

        rel_y = -lower - s["offset_y"]

        min_half_w = max(-rel_x, rel_x + W)
        min_half_h = max(-rel_y, rel_y + H)

        nW = min_half_w * 2
        nH = min_half_h * 2

        base_nW = (W * 2) if (W * 2) % 2 == 0 else (W * 2) + 1
        base_nH = (H * 2) if (H * 2) % 2 == 0 else (H * 2) + 1

        if not s["trim_margin_x"]:
            nW = max(nW, base_nW)
            nH = max(nH, base_nH)

            max_size = max(nW, nH)
            nW = max_size
            nH = max_size
        else:
            nH = max(nH, base_nH)

        if nW % 2 != 0: nW += 1
        if nH % 2 != 0: nH += 1

        pivot_x = nW // 2
        pivot_y = nH // 2

        paste_x = pivot_x + rel_x
        paste_y = pivot_y + rel_y

        new_img = Image.new("RGBA", (nW, nH), (0, 0, 0, 0))
        new_img.paste(img, (paste_x, paste_y))

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
            
            # 현재 UI에 설정된 값을 바탕으로 프리뷰 렌더링
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
            self.canvas_orig.create_rectangle(orig_x1, orig_y1, orig_x2, orig_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            res_preview = self.resize_for_preview(res_img, safe_w, safe_h)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(cx, cy, image=self.tk_res, anchor="center", tags="preview_image")

            res_w, res_h = res_preview.width, res_preview.height
            res_x1 = cx - (res_w // 2)
            res_y1 = cy - (res_h // 2)
            res_x2 = res_x1 + res_w
            res_y2 = res_y1 + res_h
            self.canvas_res.create_rectangle(res_x1, res_y1, res_x2, res_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            self.canvas_res.create_line(0, cy, c_w, cy, fill="#06b6d4", width=1, tags="crosshair")
            self.canvas_res.create_line(cx, 0, cx, c_h, fill="#06b6d4", width=1, tags="crosshair")
            
        except Exception as e:
            print(f"미리보기 업데이트 실패: {e}")

    def run_batch(self):
        target_files = [f for f in self.file_data if f["checked"]]
        
        if not target_files:
            messagebox.showwarning("안내", "체크된(☑) 파일이 없습니다.\n처리할 파일을 목록에서 체크해주세요.")
            return

        is_overwrite = self.overwrite.get()
        save_mode_val = self.save_mode.get()
        
        if is_overwrite:
            ans = messagebox.askyesno("경고", f"체크된 {len(target_files)}개 원본 파일 자체를 덮어씁니다.\n이 작업은 되돌리기로 복구할 수 없습니다.\n\n정말로 진행하시겠습니까?")
            if not ans: return
        elif save_mode_val == "single" and not self.output_dir:
            messagebox.showwarning("안내", "단일 폴더 저장 모드가 선택되었지만, 저장할 폴더가 지정되지 않았습니다.\n폴더를 먼저 선택해주세요.")
            return

        success_count = 0
        self.last_generated_files.clear()

        for idx, file_info in enumerate(target_files):
            orig_path = file_info["path"]
            target_name = file_info["name"]
            orig_name = os.path.basename(orig_path)
            
            # 파일 고유의 설정 로드
            s = file_info["settings"]

            try:
                img = Image.open(orig_path)
                res_img = self.process_image(img, s)
                
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
                
                success_count += 1
            except Exception as e:
                print(f"파일 처리 실패 ({orig_path}): {e}")
                
            if idx % 10 == 0:
                self.root.update()

        if is_overwrite:
            messagebox.showinfo("처리 완료", f"총 {success_count}개의 파일 덮어쓰기가 완료되었습니다! 🎉")
        else:
            messagebox.showinfo("처리 완료", f"체크된 {len(target_files)}개 중 {success_count}개 파일의 보정 생성이 완료되었습니다! 🎉")

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