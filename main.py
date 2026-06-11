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
        self.root.geometry("1150x650")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        self.setup_styles()

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        # 파일 관리를 위한 리스트 딕셔너리 구조: {"id": 트리뷰_ID, "path": 절대경로, "name": 파일명, "checked": bool}
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
        self.save_mode = tk.StringVar(value="original") # "original" 또는 "single"

        self.tk_orig = None
        self.tk_res = None

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
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # ==========================================
        # 1단: 좌측 패널 (파일 목록)
        # ==========================================
        frame_left = ttk.LabelFrame(main_container, text=" 📂 작업 파일 목록 ", width=300)
        frame_left.pack(side="left", fill="y", padx=(0, 10))
        frame_left.pack_propagate(False)

        frame_btns = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_btns.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Button(frame_btns, text="파일/폴더 열기", command=self.load_files_dialog, style="Primary.TButton").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(frame_btns, text="비우기", command=self.clear_list).pack(side="right", fill="x")

        # 체크박스 일괄 제어 버튼
        frame_check_btns = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_check_btns.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Button(frame_check_btns, text="전체 선택", command=self.check_all).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(frame_check_btns, text="선택 해제", command=self.uncheck_all).pack(side="right", expand=True, fill="x", padx=(2, 0))

        ttk.Label(frame_left, text="이미지를 목록으로 드래그 하세요.", style="Muted.TLabel").pack(pady=(0, 5))

        # 트리뷰 (체크박스 및 목록 표시용)
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
        # 2단: 중앙 패널 (설정 및 처리)
        # ==========================================
        frame_mid = ttk.Frame(main_container, width=320, style="TFrame")
        frame_mid.pack(side="left", fill="y", padx=(0, 10))
        frame_mid.pack_propagate(False)

        # --- 2-1: 보정 설정 프레임 ---
        lf_settings = ttk.LabelFrame(frame_mid, text=" ⚙️ 보정 설정 ")
        lf_settings.pack(fill="x", pady=(0, 10))

        offset_values = list(range(-10, 11))

        frame_y = ttk.Frame(lf_settings, style="Panel.TFrame")
        frame_y.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(frame_y, text="세로 이동 오프셋:").pack(side="left")
        cb_y = ttk.Combobox(frame_y, textvariable=self.offset_y, values=offset_values, state="readonly", width=5)
        cb_y.pack(side="left", padx=10)
        cb_y.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        frame_x = ttk.Frame(lf_settings, style="Panel.TFrame")
        frame_x.pack(fill="x", padx=15, pady=(0, 10))
        ttk.Label(frame_x, text="가로 이동 오프셋:").pack(side="left")
        cb_x = ttk.Combobox(frame_x, textvariable=self.offset_x, values=offset_values, state="readonly", width=5)
        cb_x.pack(side="left", padx=10)
        cb_x.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Checkbutton(lf_settings, text="좌우 알파 Bbox 중앙 정렬 (자동 맞춤)", variable=self.h_align, command=self.update_preview).pack(anchor="w", padx=15, pady=(0, 10))
        ttk.Label(lf_settings, text="* 캔버스는 원본의 2배 정사각형으로 확장됩니다.", style="Muted.TLabel").pack(anchor="w", padx=15, pady=(0, 15))

        # --- 2-2: 저장 방식 및 처리 프레임 ---
        lf_save = ttk.LabelFrame(frame_mid, text=" 💾 저장 옵션 및 처리 ")
        lf_save.pack(fill="both", expand=True)

        ttk.Checkbutton(lf_save, text="원본 파일에 그대로 덮어쓰기 (!주의)", variable=self.overwrite, command=self.toggle_overwrite).pack(anchor="w", padx=15, pady=(15, 5))

        ttk.Separator(lf_save).pack(fill="x", padx=15, pady=5)

        self.rb_orig = ttk.Radiobutton(lf_save, text="각 원본 파일이 있는 폴더에 각각 저장", variable=self.save_mode, value="original", command=self.toggle_save_mode)
        self.rb_orig.pack(anchor="w", padx=15, pady=5)

        self.rb_single = ttk.Radiobutton(lf_save, text="지정한 단일 폴더에 모두 모아서 저장", variable=self.save_mode, value="single", command=self.toggle_save_mode)
        self.rb_single.pack(anchor="w", padx=15, pady=5)

        self.btn_out_dir = ttk.Button(lf_save, text="📁 단일 저장 폴더 선택", command=self.select_output_dir)
        self.btn_out_dir.pack(fill="x", padx=15, pady=(5, 5))
        
        self.lbl_out_dir = ttk.Label(lf_save, text="[단일 저장 폴더 지정 안됨]", style="Muted.TLabel", wraplength=280)
        self.lbl_out_dir.pack(padx=15, pady=(0, 5))
        
        self.toggle_save_mode() # 초기 상태 연동

        # 하단 액션 버튼
        frame_actions = ttk.Frame(lf_save, style="Panel.TFrame")
        frame_actions.pack(side="bottom", fill="x", padx=15, pady=15)
        
        self.btn_undo = ttk.Button(frame_actions, text="↩ 마지막 작업 되돌리기", command=self.undo_batch)
        self.btn_undo.pack(fill="x", pady=(0, 10))
        
        ttk.Button(frame_actions, text="▶ 선택된 파일 처리 시작", style="Success.TButton", command=self.run_batch).pack(fill="x")

        # ==========================================
        # 3단: 우측 패널 (미리보기)
        # ==========================================
        frame_right = ttk.LabelFrame(main_container, text=" 👁️ 실시간 미리보기 ")
        frame_right.pack(side="left", expand=True, fill="both")

        frame_right_lbls = ttk.Frame(frame_right, style="Panel.TFrame")
        frame_right_lbls.pack(fill="x", padx=10, pady=(10, 5))
        
        ttk.Label(frame_right_lbls, text="[ 원본 캔버스 ]", font=("Malgun Gothic", 10, "bold")).pack(side="left", expand=True)
        ttk.Label(frame_right_lbls, text="[ 피봇 보정 완료 ]", font=("Malgun Gothic", 10, "bold"), foreground=PRIMARY_COLOR).pack(side="left", expand=True)

        frame_canvases = ttk.Frame(frame_right, style="Panel.TFrame")
        frame_canvases.pack(expand=True, fill="both", padx=15, pady=(0, 15))
        
        canvas_bg = "#ffffff"
        canvas_bd = 1
        canvas_relief = "solid"
        
        self.canvas_orig = tk.Canvas(frame_canvases, width=220, height=450, bg=canvas_bg, relief=canvas_relief, bd=canvas_bd, highlightthickness=0)
        self.canvas_orig.pack(side="left", expand=True)
        self.draw_checkerboard(self.canvas_orig, 220, 450)

        self.canvas_res = tk.Canvas(frame_canvases, width=220, height=450, bg=canvas_bg, relief=canvas_relief, bd=canvas_bd, highlightthickness=0)
        self.canvas_res.pack(side="left", expand=True)
        self.draw_checkerboard(self.canvas_res, 220, 450)

    # ------------------ 기능 메서드 ------------------

    def draw_checkerboard(self, canvas, width, height, size=10):
        for y in range(0, height, size):
            for x in range(0, width, size):
                color = "#ffffff" if ((x//size) + (y//size)) % 2 == 0 else "#f1f5f9"
                canvas.create_rectangle(x, y, x+size, y+size, fill=color, outline="", tags="checkerboard")
        canvas.tag_lower("checkerboard")

    def toggle_overwrite(self):
        """덮어쓰기 여부에 따라 저장 옵션 라디오 버튼들 비활성화/활성화"""
        if self.overwrite.get():
            self.rb_orig.state(['disabled'])
            self.rb_single.state(['disabled'])
            self.btn_out_dir.state(['disabled'])
            self.btn_undo.state(['disabled'])
        else:
            self.rb_orig.state(['!disabled'])
            self.rb_single.state(['!disabled'])
            self.btn_undo.state(['!disabled'])
            self.toggle_save_mode() # 라디오버튼 상태에 맞춰 단일 폴더 버튼 제어

    def toggle_save_mode(self):
        """저장 방식에 따라 단일 폴더 선택 버튼 활성화/비활성화"""
        if not self.overwrite.get():
            if self.save_mode.get() == "single":
                self.btn_out_dir.state(['!disabled'])
            else:
                self.btn_out_dir.state(['disabled'])

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
        
        # 새 항목이 추가되었고 현재 미리보기가 없다면 첫번째 새 항목을 선택
        if first_new_id and not self.preview_path:
            self.tree.selection_set(first_new_id)
            self.tree.focus(first_new_id)
            for f in self.file_data:
                if f["id"] == first_new_id:
                    self.preview_path = f["path"]
                    self.update_preview()
                    break

    def on_tree_click(self, event):
        """체크박스 열 클릭 시 상태 토글"""
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell" and column == "#1": # 첫 번째 열(체크박스)
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
        """이름 열 더블클릭 시 이름 변경"""
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell" and column == "#2": # 두 번째 열(이름)
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
                    
                    # 내부 데이터 및 트리뷰 업데이트
                    target_f["path"] = new_path
                    target_f["name"] = new_name
                    check_str = "☑" if target_f["checked"] else "☐"
                    self.tree.item(item_id, values=(check_str, new_name))
                    
                    if self.preview_path == old_path:
                        self.preview_path = new_path
                        
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
        self.canvas_orig.delete("preview_image")
        self.canvas_res.delete("preview_image")
        self.canvas_res.delete("crosshair")

    def select_output_dir(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_dir = folder_path
            self.lbl_out_dir.config(text=folder_path, foreground=PRIMARY_COLOR)
            self.save_mode.set("single") # 경로를 선택하면 자동으로 단일 폴더 모드로 변경

    def get_alpha_bbox(self, img):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img.split()[-1].getbbox()

    def process_image(self, img, offset_y, offset_x, h_align):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
            
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
        return new_img

    def resize_for_preview(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        if ratio >= 1: ratio = int(ratio)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        return img.resize((new_w, new_h), Image.Resampling.NEAREST)

    def update_preview(self):
        self.canvas_orig.delete("preview_image")
        self.canvas_res.delete("preview_image")
        self.canvas_res.delete("crosshair")
        
        if not self.preview_path or not os.path.exists(self.preview_path):
            return

        try:
            img = Image.open(self.preview_path).convert("RGBA")
            res_img = self.process_image(img, self.offset_y.get(), self.offset_x.get(), self.h_align.get())

            img_preview = self.resize_for_preview(img, 200, 430)
            self.tk_orig = ImageTk.PhotoImage(img_preview)
            self.canvas_orig.create_image(110, 225, image=self.tk_orig, anchor="center", tags="preview_image")

            orig_w, orig_h = img_preview.width, img_preview.height
            orig_x1 = 110 - (orig_w // 2)
            orig_y1 = 225 - (orig_h // 2)
            orig_x2 = orig_x1 + orig_w
            orig_y2 = orig_y1 + orig_h
            self.canvas_orig.create_rectangle(orig_x1, orig_y1, orig_x2, orig_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            res_preview = self.resize_for_preview(res_img, 200, 430)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(110, 225, image=self.tk_res, anchor="center", tags="preview_image")

            res_w, res_h = res_preview.width, res_preview.height
            res_x1 = 110 - (res_w // 2)
            res_y1 = 225 - (res_h // 2)
            res_x2 = res_x1 + res_w
            res_y2 = res_y1 + res_h
            self.canvas_res.create_rectangle(res_x1, res_y1, res_x2, res_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            self.canvas_res.create_line(0, 225, 220, 225, fill="#06b6d4", width=1, tags="crosshair")
            self.canvas_res.create_line(110, 0, 110, 450, fill="#06b6d4", width=1, tags="crosshair")
            
        except Exception as e:
            print(f"미리보기 업데이트 실패: {e}")

    def run_batch(self):
        # 체크된 파일들만 모아서 처리 타겟으로 지정
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

        self.last_generated_files.clear()

        for idx, file_info in enumerate(target_files):
            path = file_info["path"]
            try:
                img = Image.open(path)
                res_img = self.process_image(img, offset_y_val, offset_x_val, h_align_val)
                
                img.close() # 원본 이미지 닫기 (덮어쓰기를 위해)
                
                if is_overwrite:
                    save_path = path
                else:
                    basename = os.path.basename(path)
                    name, ext = os.path.splitext(basename)
                    new_filename = f"{name}_pivotfix.png"
                    
                    # 저장 모드에 따라 경로 분기
                    if save_mode_val == "single":
                        save_dir = self.output_dir
                    else: # "original"
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