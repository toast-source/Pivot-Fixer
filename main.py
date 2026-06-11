import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk

# 전체 컬러 팔레트
BG_COLOR = "#f4f5f7"
PANEL_BG = "#ffffff"
PRIMARY_COLOR = "#3b82f6"
PRIMARY_HOVER = "#2563eb"
SUCCESS_COLOR = "#10b981"
SUCCESS_HOVER = "#059669"
DANGER_COLOR = "#ef4444"
TEXT_COLOR = "#1f2937"
TEXT_MUTED = "#6b7280"
BORDER_COLOR = "#e5e7eb"

class PivotFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG 피봇 보정 툴 (Pixel Art Optimizer)")
        
        # 텍스트 잘림을 방지하고 미리보기를 넓게 주기 위해 초기 가로 너비를 더 넓게 확보 (1400x750)
        self.root.geometry("1400x750")
        self.root.minsize(1200, 650)
        self.root.resizable(True, True)
        self.root.configure(bg=BG_COLOR)

        self.setup_styles()

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        self.file_data = []
        self.preview_path = None
        self.output_dir = ""
        self.last_generated_files = [] 

        # 설정 변수
        self.offset_y = tk.IntVar(value=0)
        self.offset_x = tk.IntVar(value=0)
        self.h_align = tk.BooleanVar(value=True)
        
        # 저장 방식 관련 변수
        self.overwrite = tk.BooleanVar(value=False)
        self.save_mode = tk.StringVar(value="original") 

        # 이미지 변환(Flip/Rotate) 관련 변수
        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)
        self.rotate_angle = tk.StringVar(value="0도 (회전 없음)")
        self.transform_order = tk.StringVar(value="before")

        self.tk_orig = None
        self.tk_res = None
        self._resize_timer = None

        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        default_font = ("Malgun Gothic", 10)
        bold_font = ("Malgun Gothic", 10, "bold")

        style.configure("TFrame", background=BG_COLOR)
        style.configure("Panel.TFrame", background=PANEL_BG)

        style.configure("TLabelframe", background=PANEL_BG, borderwidth=1, bordercolor=BORDER_COLOR)
        style.configure("TLabelframe.Label", background=PANEL_BG, foreground=PRIMARY_COLOR, font=("Malgun Gothic", 11, "bold"), padding=(5, 5))

        style.configure("TLabel", background=PANEL_BG, foreground=TEXT_COLOR, font=default_font)
        style.configure("Muted.TLabel", foreground=TEXT_MUTED, font=("Malgun Gothic", 9))
        style.configure("Danger.TLabel", foreground=DANGER_COLOR, font=bold_font)
        style.configure("Success.TLabel", foreground=SUCCESS_COLOR, font=bold_font)

        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT_COLOR, font=default_font)
        style.map("TCheckbutton", background=[("active", PANEL_BG)])

        style.configure("TRadiobutton", background=PANEL_BG, foreground=TEXT_COLOR, font=default_font)
        style.map("TRadiobutton", background=[("active", PANEL_BG)])

        style.configure("TCombobox", padding=5, font=default_font)

        style.configure("TButton", font=default_font, padding=6, background="#ffffff", borderwidth=1, bordercolor=BORDER_COLOR)
        style.map("TButton", background=[("active", "#f3f4f6")])

        style.configure("Primary.TButton", font=bold_font, padding=6, background=PRIMARY_COLOR, foreground="white", borderwidth=0)
        style.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])

        style.configure("Success.TButton", font=("Malgun Gothic", 12, "bold"), padding=10, background=SUCCESS_COLOR, foreground="white", borderwidth=0)
        style.map("Success.TButton", background=[("active", SUCCESS_HOVER)])

        style.configure("Treeview", font=default_font, rowheight=25, background="#f8fafc", fieldbackground="#f8fafc")
        style.configure("Treeview.Heading", font=bold_font, background="#e5e7eb")
        style.map("Treeview", background=[('selected', PRIMARY_COLOR)], foreground=[('selected', 'white')])

    def setup_ui(self):
        self.paned_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_main.pack(fill="both", expand=True, padx=10, pady=10)

        # ==========================================
        # 1단: 좌측 패널 (파일 목록)
        # ==========================================
        # 파일 목록 영역은 너무 넓을 필요가 없으므로 고정 느낌의 가중치(1) 부여
        frame_left = ttk.LabelFrame(self.paned_main, text=" 📂 작업 파일 목록 ")
        self.paned_main.add(frame_left, weight=1)

        frame_btns = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_btns.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Button(frame_btns, text="파일/폴더 열기", command=self.load_files_dialog, style="Primary.TButton").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(frame_btns, text="비우기", command=self.clear_list).pack(side="right", fill="x")

        frame_check_btns = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_check_btns.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Button(frame_check_btns, text="전체 선택", command=self.check_all).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(frame_check_btns, text="선택 해제", command=self.uncheck_all).pack(side="right", expand=True, fill="x", padx=(2, 0))

        ttk.Label(frame_left, text="이미지를 목록으로 드래그 하세요.", style="Muted.TLabel").pack(pady=(0, 5))

        frame_list = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_list.pack(expand=True, fill="both", padx=10, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(frame_list)
        scrollbar.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(frame_list, columns=("check", "name"), show="headings", yscrollcommand=scrollbar.set, selectmode="browse")
        self.tree.heading("check", text="선택")
        self.tree.column("check", width=40, anchor="center", stretch=False)
        self.tree.heading("name", text="파일 이름 (더블클릭 수정)", anchor="w")
        self.tree.column("name", anchor="w", stretch=True)
        self.tree.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)

        self.lbl_input_info = ttk.Label(frame_left, text="선택됨: 0개 / 전체: 0개", font=("Malgun Gothic", 10, "bold"), foreground=PRIMARY_COLOR)
        self.lbl_input_info.pack(pady=(5, 10))

        # ==========================================
        # 2단: 중앙 패널 (설정 및 처리) - 넓이 확장 및 스크롤 최적화
        # ==========================================
        # 텍스트 잘림 현상을 방지하기 위해 weight=2 로 설정하여 좌측보다 넓게 초기 할당
        frame_mid_container = ttk.LabelFrame(self.paned_main, text=" ⚙️ 보정 및 변환 설정 ")
        self.paned_main.add(frame_mid_container, weight=2)

        mid_canvas = tk.Canvas(frame_mid_container, bg=PANEL_BG, highlightthickness=0)
        mid_scrollbar = ttk.Scrollbar(frame_mid_container, orient="vertical", command=mid_canvas.yview)
        frame_mid = ttk.Frame(mid_canvas, style="Panel.TFrame")
        
        frame_mid.bind("<Configure>", lambda e: mid_canvas.configure(scrollregion=mid_canvas.bbox("all")))
        canvas_window = mid_canvas.create_window((0, 0), window=frame_mid, anchor="nw")
        mid_canvas.bind("<Configure>", lambda e: mid_canvas.itemconfig(canvas_window, width=e.width))

        mid_canvas.pack(side="left", fill="both", expand=True)
        mid_scrollbar.pack(side="right", fill="y")
        mid_canvas.configure(yscrollcommand=mid_scrollbar.set)

        # --- 2-1: 이미지 변환 설정 프레임 ---
        lf_transform = ttk.LabelFrame(frame_mid, text=" 🔄 이미지 변환 (회전/반전) ")
        lf_transform.pack(fill="x", padx=10, pady=(10, 10))

        ttk.Label(lf_transform, text="변환 적용 시점:").pack(anchor="w", padx=10, pady=(10, 5))
        # 텍스트가 잘리지 않도록 폰트 크기를 유지하되 패딩 간격을 최적화
        ttk.Radiobutton(lf_transform, text="이미지 먼저 변환 후 → 피봇 보정 (추천)", variable=self.transform_order, value="before", command=self.update_preview).pack(anchor="w", padx=20, pady=2)
        ttk.Radiobutton(lf_transform, text="피봇 먼저 보정 후 → 캔버스 전체 변환", variable=self.transform_order, value="after", command=self.update_preview).pack(anchor="w", padx=20, pady=(2, 10))

        frame_flips = ttk.Frame(lf_transform, style="Panel.TFrame")
        frame_flips.pack(fill="x", padx=15, pady=5)
        ttk.Checkbutton(frame_flips, text="가로 뒤집기", variable=self.flip_h, command=self.update_preview).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(frame_flips, text="세로 뒤집기", variable=self.flip_v, command=self.update_preview).pack(side="left")

        frame_rot = ttk.Frame(lf_transform, style="Panel.TFrame")
        frame_rot.pack(fill="x", padx=15, pady=(5, 15))
        ttk.Label(frame_rot, text="회전 각도:").pack(side="left")
        rot_values = ["0도 (회전 없음)", "90도 (시계방향)", "180도", "270도 (시계방향)"]
        cb_rot = ttk.Combobox(frame_rot, textvariable=self.rotate_angle, values=rot_values, state="readonly", width=18)
        cb_rot.pack(side="left", padx=10)
        cb_rot.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        # --- 2-2: 피봇 위치 설정 프레임 ---
        lf_pivot = ttk.LabelFrame(frame_mid, text=" 🎯 피봇 보정 설정 ")
        lf_pivot.pack(fill="x", padx=10, pady=(0, 10))

        offset_values = list(range(-10, 11))

        frame_y = ttk.Frame(lf_pivot, style="Panel.TFrame")
        frame_y.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(frame_y, text="세로 이동 오프셋:").pack(side="left")
        cb_y = ttk.Combobox(frame_y, textvariable=self.offset_y, values=offset_values, state="readonly", width=5)
        cb_y.pack(side="left", padx=10)
        cb_y.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        frame_x = ttk.Frame(lf_pivot, style="Panel.TFrame")
        frame_x.pack(fill="x", padx=15, pady=(0, 10))
        ttk.Label(frame_x, text="가로 이동 오프셋:").pack(side="left")
        cb_x = ttk.Combobox(frame_x, textvariable=self.offset_x, values=offset_values, state="readonly", width=5)
        cb_x.pack(side="left", padx=10)
        cb_x.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Checkbutton(lf_pivot, text="좌우 알파 Bbox 중앙 정렬 (자동 맞춤)", variable=self.h_align, command=self.update_preview).pack(anchor="w", padx=15, pady=(0, 5))
        ttk.Label(lf_pivot, text="* 캔버스는 원본의 2배 정사각형으로 확장됩니다.", style="Muted.TLabel").pack(anchor="w", padx=15, pady=(0, 15))

        # --- 2-3: 저장 옵션 프레임 ---
        lf_save = ttk.LabelFrame(frame_mid, text=" 💾 저장 옵션 ")
        lf_save.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Checkbutton(lf_save, text="원본 파일에 덮어쓰기 (!주의)", variable=self.overwrite, command=self.toggle_overwrite).pack(anchor="w", padx=15, pady=(15, 5))
        ttk.Separator(lf_save).pack(fill="x", padx=15, pady=5)
        
        # 텍스트 길이를 최적화하여 좁은 창에서도 잘리지 않도록 함
        self.rb_orig = ttk.Radiobutton(lf_save, text="각 원본 폴더에 '_pivotfix' 추가", variable=self.save_mode, value="original", command=self.toggle_save_mode)
        self.rb_orig.pack(anchor="w", padx=15, pady=5)
        self.rb_single = ttk.Radiobutton(lf_save, text="지정한 단일 폴더에 모두 저장", variable=self.save_mode, value="single", command=self.toggle_save_mode)
        self.rb_single.pack(anchor="w", padx=15, pady=5)

        self.btn_out_dir = ttk.Button(lf_save, text="📁 단일 저장 폴더 선택", command=self.select_output_dir)
        self.btn_out_dir.pack(fill="x", padx=15, pady=(5, 5))
        self.lbl_out_dir = ttk.Label(lf_save, text="[폴더 미지정]", style="Muted.TLabel", wraplength=300)
        self.lbl_out_dir.pack(padx=15, pady=(0, 15))
        
        self.toggle_save_mode() 

        # 하단 액션 버튼
        frame_actions = ttk.Frame(frame_mid, style="Panel.TFrame")
        frame_actions.pack(fill="x", padx=10, pady=(0, 20))
        
        self.btn_undo = ttk.Button(frame_actions, text="↩ 마지막 작업 되돌리기", command=self.undo_batch)
        self.btn_undo.pack(fill="x", pady=(0, 10))
        ttk.Button(frame_actions, text="▶ 선택된 파일 처리 시작", style="Success.TButton", command=self.run_batch).pack(fill="x")

        # ==========================================
        # 3단: 우측 패널 (미리보기 - 반응형 최적화)
        # ==========================================
        # 미리보기 패널에 가장 높은 가중치(4)를 주어 창을 키우면 주로 이 영역이 늘어나도록 하고, 찌그러짐을 방지함
        frame_right = ttk.LabelFrame(self.paned_main, text=" 👁️ 실시간 미리보기 (반응형) ")
        self.paned_main.add(frame_right, weight=4)

        frame_right_lbls = ttk.Frame(frame_right, style="Panel.TFrame")
        frame_right_lbls.pack(fill="x", padx=10, pady=(10, 5))
        
        ttk.Label(frame_right_lbls, text="[ 원본 캔버스 ]", font=("Malgun Gothic", 10, "bold")).pack(side="left", expand=True)
        ttk.Label(frame_right_lbls, text="[ 변환 및 보정 완료 ]", font=("Malgun Gothic", 10, "bold"), foreground=PRIMARY_COLOR).pack(side="left", expand=True)

        self.frame_canvases = ttk.Frame(frame_right, style="Panel.TFrame")
        # fill="both", expand=True 옵션으로 프레임이 부모 크기에 맞춰 상하좌우로 꽉 차게 됨
        self.frame_canvases.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        canvas_bg = "#ffffff"
        canvas_bd = 1
        canvas_relief = "solid"
        
        # 캔버스 두 개를 나란히 배치. expand=True, fill="both" 로 종횡비를 화면에 맞춤.
        self.canvas_orig = tk.Canvas(self.frame_canvases, bg=canvas_bg, relief=canvas_relief, bd=canvas_bd, highlightthickness=0)
        self.canvas_orig.pack(side="left", expand=True, fill="both", padx=(0, 5))

        self.canvas_res = tk.Canvas(self.frame_canvases, bg=canvas_bg, relief=canvas_relief, bd=canvas_bd, highlightthickness=0)
        self.canvas_res.pack(side="left", expand=True, fill="both", padx=(5, 0))

        self.frame_canvases.bind("<Configure>", self.on_canvas_resize)

    # ------------------ 기능 메서드 ------------------

    def on_canvas_resize(self, event):
        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(100, self.update_preview)

    def draw_checkerboard(self, canvas, width, height, size=10):
        # 최적화: 이전에 그려진 체커보드를 삭제
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
        self.lbl_input_info.config(text=f"선택됨: {checked_count}개 / 전체: {total_count}개")

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
        for p in new_paths:
            p_norm = os.path.normpath(p)
            if not any(f["path"] == p_norm for f in self.file_data):
                name = os.path.basename(p_norm)
                item_id = self.tree.insert("", tk.END, values=("☑", name))
                self.file_data.append({"id": item_id, "path": p_norm, "name": name, "checked": True})
                if first_new_id is None:
                    first_new_id = item_id
                
        self.update_selection_info()
        
        if first_new_id and not self.preview_path:
            self.tree.selection_set(first_new_id)
            self.tree.focus(first_new_id)
            for f in self.file_data:
                if f["id"] == first_new_id:
                    self.preview_path = f["path"]
                    self.update_preview()
                    break

    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell" and column == "#1":
            item_id = self.tree.identify_row(event.y)
            if item_id:
                for f in self.file_data:
                    if f["id"] == item_id:
                        f["checked"] = not f["checked"]
                        check_str = "☑" if f["checked"] else "☐"
                        self.tree.item(item_id, values=(check_str, f["name"]))
                        self.update_selection_info()
                        break

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            for f in self.file_data:
                if f["id"] == item_id:
                    self.preview_path = f["path"]
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
            
            old_path = target_f["path"]
            old_dir = os.path.dirname(old_path)
            old_name = target_f["name"]
            
            new_name = simpledialog.askstring("이름 변경", "새 파일 이름을 입력하세요:", initialvalue=old_name, parent=self.root)
            
            if new_name and new_name != old_name:
                if not new_name.lower().endswith(".png"):
                    new_name += ".png"
                    
                new_path = os.path.join(old_dir, new_name)
                
                if os.path.exists(new_path):
                    messagebox.showerror("오류", "동일한 이름을 가진 파일이 이미 존재합니다.")
                    return
                    
                try:
                    os.rename(old_path, new_path)
                    target_f["path"] = new_path
                    target_f["name"] = new_name
                    check_str = "☑" if target_f["checked"] else "☐"
                    self.tree.item(item_id, values=(check_str, new_name))
                    
                    if self.preview_path == old_path:
                        self.preview_path = new_path
                        self.update_preview()
                        
                except Exception as e:
                    messagebox.showerror("오류", f"이름 변경 실패: {e}")

    def check_all(self):
        for f in self.file_data:
            if not f["checked"]:
                f["checked"] = True
                self.tree.item(f["id"], values=("☑", f["name"]))
        self.update_selection_info()

    def uncheck_all(self):
        for f in self.file_data:
            if f["checked"]:
                f["checked"] = False
                self.tree.item(f["id"], values=("☐", f["name"]))
        self.update_selection_info()

    def clear_list(self):
        self.file_data.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.preview_path = None
        self.update_selection_info()
        self.canvas_orig.delete("all")
        self.canvas_res.delete("all")

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

    def apply_transformations(self, img):
        """UI에 설정된 뒤집기 및 회전을 순서대로 이미지에 적용합니다."""
        if self.flip_h.get():
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if self.flip_v.get():
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
        rot_val = self.rotate_angle.get()
        if "90도" in rot_val:
            img = img.transpose(Image.ROTATE_270) # PIL의 90도는 반시계방향이므로 270을 써서 시계방향 90도를 맞춤
        elif "180도" in rot_val:
            img = img.transpose(Image.ROTATE_180)
        elif "270도" in rot_val:
            img = img.transpose(Image.ROTATE_90)
            
        return img

    def process_image(self, img, offset_y, offset_x, h_align, order):
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # 1. '이미지 변환 후 피봇 보정' 옵션 시 원본 이미지를 먼저 변환
        if order == "before":
            img = self.apply_transformations(img)
            
        W, H = img.size
        bbox = self.get_alpha_bbox(img)
        
        if bbox is None:
            left, upper, right, lower = 0, 0, W, H
        else:
            left, upper, right, lower = bbox

        if h_align:
            cx_visible = (left + right) // 2
            rel_x = -cx_visible + offset_x
        else:
            rel_x = -(W // 2) + offset_x

        rel_y = -lower - offset_y

        min_half_w = max(-rel_x, rel_x + W)
        min_half_h = max(-rel_y, rel_y + H)

        nW = min_half_w * 2
        nH = min_half_h * 2

        base_nW = (W * 2) if (W * 2) % 2 == 0 else (W * 2) + 1
        base_nH = (H * 2) if (H * 2) % 2 == 0 else (H * 2) + 1

        nW = max(nW, base_nW)
        nH = max(nH, base_nH)

        max_size = max(nW, nH)
        nW = max_size
        nH = max_size

        if nW % 2 != 0: nW += 1
        if nH % 2 != 0: nH += 1

        pivot_x = nW // 2
        pivot_y = nH // 2

        paste_x = pivot_x + rel_x
        paste_y = pivot_y + rel_y

        new_img = Image.new("RGBA", (nW, nH), (0, 0, 0, 0))
        new_img.paste(img, (paste_x, paste_y))

        # 2. '피봇 보정 후 캔버스 변환' 옵션 시 만들어진 넓은 캔버스 전체를 변환
        if order == "after":
            new_img = self.apply_transformations(new_img)

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
        
        # 캔버스가 아직 그려지지 않아 너비/높이가 1px인 경우 렌더링 무시
        if c_w <= 1 or c_h <= 1: return

        self.draw_checkerboard(self.canvas_orig, c_w, c_h)
        self.draw_checkerboard(self.canvas_res, c_w, c_h)

        if not self.preview_path or not os.path.exists(self.preview_path):
            return

        try:
            img = Image.open(self.preview_path).convert("RGBA")
            order = self.transform_order.get()
            res_img = self.process_image(img, self.offset_y.get(), self.offset_x.get(), self.h_align.get(), order)

            # 패딩 40을 주어 여백을 남기고 스케일링 (가로세로 비율 최적화)
            safe_w = c_w - 40
            safe_h = c_h - 40
            if safe_w < 10 or safe_h < 10: return
            
            cx = c_w // 2
            cy = c_h // 2

            # 원본 미리보기
            img_preview = self.resize_for_preview(img, safe_w, safe_h)
            self.tk_orig = ImageTk.PhotoImage(img_preview)
            self.canvas_orig.create_image(cx, cy, image=self.tk_orig, anchor="center", tags="preview_image")

            orig_w, orig_h = img_preview.width, img_preview.height
            orig_x1 = cx - (orig_w // 2)
            orig_y1 = cy - (orig_h // 2)
            orig_x2 = orig_x1 + orig_w
            orig_y2 = orig_y1 + orig_h
            self.canvas_orig.create_rectangle(orig_x1, orig_y1, orig_x2, orig_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            # 결과 미리보기
            res_preview = self.resize_for_preview(res_img, safe_w, safe_h)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(cx, cy, image=self.tk_res, anchor="center", tags="preview_image")

            res_w, res_h = res_preview.width, res_preview.height
            res_x1 = cx - (res_w // 2)
            res_y1 = cy - (res_h // 2)
            res_x2 = res_x1 + res_w
            res_y2 = res_y1 + res_h
            self.canvas_res.create_rectangle(res_x1, res_y1, res_x2, res_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            # 십자선 동적 생성
            self.canvas_res.create_line(0, cy, c_w, cy, fill="#06b6d4", width=1, tags="crosshair")
            self.canvas_res.create_line(cx, 0, cx, c_h, fill="#06b6d4", width=1, tags="crosshair")
            
        except Exception as e:
            print(f"미리보기 업데이트 실패: {e}")

    def run_batch(self):
        target_files = [f for f in self.file_data if f["checked"]]
        
        if not target_files:
            messagebox.showwarning("안내", "체크된(선택된) 파일이 없습니다.\n처리할 파일을 목록에서 체크해주세요.")
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
        h_align_val = self.h_align.get()
        offset_y_val = self.offset_y.get()
        offset_x_val = self.offset_x.get()
        order = self.transform_order.get()

        self.last_generated_files.clear()

        for idx, file_info in enumerate(target_files):
            path = file_info["path"]
            try:
                img = Image.open(path)
                res_img = self.process_image(img, offset_y_val, offset_x_val, h_align_val, order)
                
                img.close() 
                
                if is_overwrite:
                    save_path = path
                else:
                    basename = os.path.basename(path)
                    name, ext = os.path.splitext(basename)
                    new_filename = f"{name}_pivotfix.png"
                    
                    if save_mode_val == "single":
                        save_dir = self.output_dir
                    else: 
                        save_dir = os.path.dirname(path)
                        
                    save_path = os.path.join(save_dir, new_filename)
                    self.last_generated_files.append(save_path) 
                
                res_img.save(save_path, "PNG")
                success_count += 1
            except Exception as e:
                print(f"파일 처리 실패 ({path}): {e}")
                
            if idx % 10 == 0:
                self.root.update()

        if is_overwrite:
            messagebox.showinfo("처리 완료", f"총 {success_count}개의 파일 덮어쓰기가 완료되었습니다! 🎉")
        else:
            messagebox.showinfo("처리 완료", f"선택된 {len(target_files)}개 중 {success_count}개 파일의 보정 생성이 완료되었습니다! 🎉")

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