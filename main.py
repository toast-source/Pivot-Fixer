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

        # ttk 스타일 전역 설정
        self.setup_styles()

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        self.input_paths = []
        self.preview_path = None
        self.output_dir = ""
        self.last_generated_files = [] 

        # 설정 변수 (-10 ~ 10 지원)
        self.offset_y = tk.IntVar(value=0)
        self.offset_x = tk.IntVar(value=0) # 새로 추가된 가로 이동 변수
        self.h_align = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)

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

        style.configure("TCombobox", padding=5, font=default_font)

        style.configure("TButton", font=default_font, padding=6, background="#ffffff", borderwidth=1, bordercolor=BORDER_COLOR)
        style.map("TButton", background=[("active", "#f3f4f6")])

        style.configure("Primary.TButton", font=bold_font, padding=6, background=PRIMARY_COLOR, foreground="white", borderwidth=0)
        style.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])

        style.configure("Success.TButton", font=("Malgun Gothic", 12, "bold"), padding=10, background=SUCCESS_COLOR, foreground="white", borderwidth=0)
        style.map("Success.TButton", background=[("active", SUCCESS_HOVER)])

        style.configure("TScrollbar", background="#e5e7eb", troughcolor=PANEL_BG, borderwidth=0, arrowsize=12)

    def setup_ui(self):
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # ==========================================
        # 1단: 좌측 패널 (파일 목록)
        # ==========================================
        frame_left = ttk.LabelFrame(main_container, text=" 📂 파일 목록 ", width=300)
        frame_left.pack(side="left", fill="y", padx=(0, 10))
        frame_left.pack_propagate(False)

        frame_btns = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_btns.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Button(frame_btns, text="파일/폴더 열기", command=self.load_files_dialog, style="Primary.TButton").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(frame_btns, text="비우기", command=self.clear_list).pack(side="right", fill="x")

        ttk.Label(frame_left, text="이곳으로 이미지를 드래그 앤 드롭 하세요.", style="Muted.TLabel").pack(pady=5)

        frame_list = ttk.Frame(frame_left, style="Panel.TFrame")
        frame_list.pack(expand=True, fill="both", padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(frame_list)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox = tk.Listbox(
            frame_list, 
            yscrollcommand=scrollbar.set, 
            selectmode="single", 
            font=("Malgun Gothic", 10),
            bg="#f8fafc", 
            fg=TEXT_COLOR, 
            selectbackground=PRIMARY_COLOR, 
            selectforeground="white",
            relief="flat", 
            highlightthickness=1, 
            highlightbackground=BORDER_COLOR
        )
        self.listbox.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.listbox.yview)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)
        self.listbox.bind('<Double-Button-1>', self.on_list_double_click)

        ttk.Label(frame_left, text="💡 팁: 더블클릭하여 파일 이름을 바꿀 수 있습니다.", style="Muted.TLabel").pack(pady=(2, 5))
        self.lbl_input_info = ttk.Label(frame_left, text="선택된 파일: 0개", font=("Malgun Gothic", 10, "bold"), foreground=PRIMARY_COLOR)
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

        # 오프셋 범위 배열 (-10 ~ +10)
        offset_values = list(range(-10, 11))

        # 세로 보정 설정
        frame_y = ttk.Frame(lf_settings, style="Panel.TFrame")
        frame_y.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(frame_y, text="세로 이동 오프셋:").pack(side="left")
        cb_y = ttk.Combobox(frame_y, textvariable=self.offset_y, values=offset_values, state="readonly", width=5)
        cb_y.pack(side="left", padx=10)
        cb_y.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        # 가로 보정 설정
        frame_x = ttk.Frame(lf_settings, style="Panel.TFrame")
        frame_x.pack(fill="x", padx=15, pady=(0, 10))
        ttk.Label(frame_x, text="가로 이동 오프셋:").pack(side="left")
        cb_x = ttk.Combobox(frame_x, textvariable=self.offset_x, values=offset_values, state="readonly", width=5)
        cb_x.pack(side="left", padx=10)
        cb_x.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Checkbutton(lf_settings, text="좌우 알파 Bbox 중앙 정렬 (자동 맞춤)", variable=self.h_align, command=self.update_preview).pack(anchor="w", padx=15, pady=(0, 10))
        ttk.Label(lf_settings, text="* 캔버스 넓이는 원본의 약 2배로 자동 확장됩니다.", style="Muted.TLabel").pack(anchor="w", padx=15, pady=(0, 15))

        # --- 2-2: 저장 및 처리 프레임 ---
        lf_save = ttk.LabelFrame(frame_mid, text=" 💾 저장 및 처리 ")
        lf_save.pack(fill="both", expand=True)

        ttk.Checkbutton(lf_save, text="원본 파일에 그대로 덮어쓰기 (!주의)", variable=self.overwrite, command=self.toggle_overwrite).pack(anchor="w", padx=15, pady=(15, 5))

        self.btn_out_dir = ttk.Button(lf_save, text="📁 다른 저장 폴더 선택", command=self.select_output_dir)
        self.btn_out_dir.pack(fill="x", padx=15, pady=(10, 5))
        
        self.lbl_out_dir = ttk.Label(lf_save, text="기본값: 원본 폴더에 '_pivotfix' 추가", style="Muted.TLabel", wraplength=280)
        self.lbl_out_dir.pack(padx=15, pady=(0, 15))

        # 하단 액션 버튼
        frame_actions = ttk.Frame(lf_save, style="Panel.TFrame")
        frame_actions.pack(side="bottom", fill="x", padx=15, pady=15)
        
        self.btn_undo = ttk.Button(frame_actions, text="↩ 마지막 작업 되돌리기", command=self.undo_batch)
        self.btn_undo.pack(fill="x", pady=(0, 10))
        
        ttk.Button(frame_actions, text="▶ 처리 시작", style="Success.TButton", command=self.run_batch).pack(fill="x")

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
        if self.overwrite.get():
            self.btn_out_dir.state(['disabled'])
            self.btn_undo.state(['disabled'])
            self.lbl_out_dir.config(text="원본 이미지 자체를 덮어씁니다.\n되돌릴 수 없으니 주의하세요!", foreground=DANGER_COLOR)
        else:
            self.btn_out_dir.state(['!disabled'])
            self.btn_undo.state(['!disabled'])
            if self.output_dir:
                self.lbl_out_dir.config(text=self.output_dir, foreground=TEXT_MUTED)
            else:
                self.lbl_out_dir.config(text="기본값: 원본 폴더에 '_pivotfix' 추가", foreground=TEXT_MUTED)

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
        for p in new_paths:
            p_norm = os.path.normpath(p)
            if p_norm not in [os.path.normpath(ip) for ip in self.input_paths]:
                self.input_paths.append(p_norm)
                self.listbox.insert(tk.END, os.path.basename(p_norm))
                
        self.lbl_input_info.config(text=f"선택된 파일: {len(self.input_paths)}개")
        
        if self.input_paths and not self.preview_path:
            self.listbox.selection_set(0)
            self.preview_path = self.input_paths[0]
            self.update_preview()

    def on_list_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.preview_path = self.input_paths[idx]
            self.update_preview()

    def on_list_double_click(self, event):
        selection = self.listbox.curselection()
        if not selection: return
        
        idx = selection[0]
        old_path = self.input_paths[idx]
        old_dir = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)
        
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
                self.input_paths[idx] = new_path
                self.listbox.delete(idx)
                self.listbox.insert(idx, new_name)
                self.listbox.selection_set(idx)
                
                if self.preview_path == old_path:
                    self.preview_path = new_path
                    
            except Exception as e:
                messagebox.showerror("오류", f"이름 변경 실패: {e}")

    def clear_list(self):
        self.input_paths.clear()
        self.listbox.delete(0, tk.END)
        self.preview_path = None
        self.lbl_input_info.config(text="선택된 파일: 0개")
        self.canvas_orig.delete("preview_image")
        self.canvas_res.delete("preview_image")
        self.canvas_res.delete("crosshair")

    def select_output_dir(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_dir = folder_path
            self.lbl_out_dir.config(text=folder_path, foreground=PRIMARY_COLOR)
        else:
            self.output_dir = ""
            self.lbl_out_dir.config(text="기본값: 원본 폴더에 '_pivotfix' 추가", foreground=TEXT_MUTED)

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

        # 가로(X) 배치 기준: h_align 활성화 시 알파 Bounding Box 중앙, 아닐 시 캔버스 중앙
        # offset_x: 음수(-)면 왼쪽, 양수(+)면 오른쪽
        if h_align:
            cx_visible = (left + right) // 2
            rel_x = -cx_visible + offset_x
        else:
            rel_x = -(W // 2) + offset_x

        # 세로(Y) 배치 기준: 하단(lower) 픽셀이 피봇 중앙선 바로 위에 얹히도록
        # 직관성 반영: 음수(-) 입력 시 이미지가 아래로 내려감, 양수(+) 입력 시 위로 올라감
        rel_y = -lower - offset_y

        # 이미지가 절대 잘리지 않기 위해 십자선 기준 상하좌우로 필요한 최소 공간 계산
        min_half_w = max(-rel_x, rel_x + W)
        min_half_h = max(-rel_y, rel_y + H)

        nW = min_half_w * 2
        nH = min_half_h * 2

        # 기본적으로 원본의 2배 크기는 유지 (최소 여백 보장)
        base_nW = (W * 2) if (W * 2) % 2 == 0 else (W * 2) + 1
        base_nH = (H * 2) if (H * 2) % 2 == 0 else (H * 2) + 1

        nW = max(nW, base_nW)
        nH = max(nH, base_nH)

        # 캔버스를 항상 정사각형으로 강제 (가장 긴 변 기준)
        max_size = max(nW, nH)
        nW = max_size
        nH = max_size

        # 짝수 강제 (0.5px 오차 방지)
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

            # 원본 이미지의 Bounding Box (크기) 계산 및 그리기
            orig_w, orig_h = img_preview.width, img_preview.height
            orig_x1 = 110 - (orig_w // 2)
            orig_y1 = 225 - (orig_h // 2)
            orig_x2 = orig_x1 + orig_w
            orig_y2 = orig_y1 + orig_h
            self.canvas_orig.create_rectangle(orig_x1, orig_y1, orig_x2, orig_y2, outline="#ef4444", dash=(2, 2), tags="preview_image")

            res_preview = self.resize_for_preview(res_img, 200, 430)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(110, 225, image=self.tk_res, anchor="center", tags="preview_image")

            # 최종 보정된 이미지의 Bounding Box (크기) 계산 및 그리기
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
        if not self.input_paths:
            messagebox.showwarning("안내", "먼저 이미지를 추가해주세요.")
            return

        is_overwrite = self.overwrite.get()
        
        if is_overwrite:
            ans = messagebox.askyesno("경고", "원본 파일 자체를 덮어씁니다.\n이 작업은 되돌리기로 복구할 수 없습니다.\n\n정말로 진행하시겠습니까?")
            if not ans: return

        success_count = 0
        h_align_val = self.h_align.get()
        offset_y_val = self.offset_y.get()
        offset_x_val = self.offset_x.get()

        self.last_generated_files.clear()

        for idx, path in enumerate(self.input_paths):
            try:
                img = Image.open(path)
                res_img = self.process_image(img, offset_y_val, offset_x_val, h_align_val)
                
                img.close()
                
                if is_overwrite:
                    save_path = path
                else:
                    basename = os.path.basename(path)
                    name, ext = os.path.splitext(basename)
                    new_filename = f"{name}_pivotfix.png"
                    save_dir = self.output_dir if self.output_dir else os.path.dirname(path)
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
            messagebox.showinfo("처리 완료", f"총 {len(self.input_paths)}개 중 {success_count}개 파일의 보정 생성이 완료되었습니다! 🎉")

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
        print("requirements.txt의 패키지가 정상적으로 설치되었는지 확인해주세요.")
        root = tk.Tk()
        
    app = PivotFixerApp(root)
    root.mainloop()