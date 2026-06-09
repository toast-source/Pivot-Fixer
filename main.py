import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk

class PivotFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG 피봇 보정 툴 (픽셀 아트 최적화)")
        # UI 레이아웃을 3단(리스트, 설정, 미리보기)으로 분할하기 위해 넉넉한 창 크기 설정
        self.root.geometry("1150x600")
        self.root.resizable(False, False)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        self.input_paths = []
        self.preview_path = None
        self.output_dir = ""
        self.last_generated_files = [] # 되돌리기용 백업 리스트

        # 설정 변수들
        self.offset_y = tk.IntVar(value=0)
        self.h_align = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)

        self.tk_orig = None
        self.tk_res = None

        self.setup_ui()

    def setup_ui(self):
        # ==========================================
        # 1단: 좌측 패널 (파일 목록)
        # ==========================================
        frame_left = tk.Frame(self.root, padx=10, pady=10, width=280)
        frame_left.pack(side="left", fill="y")
        frame_left.pack_propagate(False)

        tk.Label(frame_left, text="[ 1. 파일 목록 ]", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        
        frame_btns = tk.Frame(frame_left)
        frame_btns.pack(fill="x", pady=2)
        tk.Button(frame_btns, text="파일/폴더 열기", command=self.load_files_dialog, width=15).pack(side="left", expand=True, fill="x", padx=(0, 2))
        tk.Button(frame_btns, text="목록 비우기", command=self.clear_list, width=10).pack(side="right", expand=True, fill="x", padx=(2, 0))

        tk.Label(frame_left, text="여기로 PNG를 드래그 앤 드롭 하세요", fg="gray", font=("Arial", 9)).pack(pady=5)

        # 리스트 박스 + 스크롤바
        frame_list = tk.Frame(frame_left)
        frame_list.pack(expand=True, fill="both")
        
        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox = tk.Listbox(frame_list, yscrollcommand=scrollbar.set, selectmode="single")
        self.listbox.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.listbox.yview)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)

        self.lbl_input_info = tk.Label(frame_left, text="선택된 파일: 0개", fg="blue")
        self.lbl_input_info.pack(pady=(5, 0))

        # ==========================================
        # 2단: 중앙 패널 (설정 및 처리)
        # ==========================================
        frame_mid = tk.Frame(self.root, padx=10, pady=10, width=280)
        frame_mid.pack(side="left", fill="y")
        frame_mid.pack_propagate(False)

        tk.Label(frame_mid, text="[ 2. 보정 설정 ]", font=("Arial", 10, "bold")).pack(pady=(0, 10))
        
        # 세로 보정 설정
        frame_y = tk.Frame(frame_mid)
        frame_y.pack(pady=5, anchor="w")
        tk.Label(frame_y, text="세로 보정값 (px):").pack(side="left")
        cb_y = ttk.Combobox(frame_y, textvariable=self.offset_y, values=[0, 1, 2, 3, 4, 5, 6], state="readonly", width=5)
        cb_y.pack(side="left", padx=5)
        cb_y.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        # 좌우 보정 설정
        chk_h = tk.Checkbutton(frame_mid, text="좌우 피봇 보정 (보이는 영역 중앙정렬)", variable=self.h_align, command=self.update_preview)
        chk_h.pack(pady=5, anchor="w")

        # 캔버스 크기 안내
        tk.Label(frame_mid, text="* 캔버스 넓이는 원본의 약 2배로 확장됩니다.", fg="green", font=("Arial", 9)).pack(pady=(0, 15), anchor="w")

        tk.Label(frame_mid, text="[ 3. 저장 및 처리 ]", font=("Arial", 10, "bold")).pack(pady=(10, 10))

        # 덮어쓰기 옵션
        chk_ow = tk.Checkbutton(frame_mid, text="원본 파일 덮어쓰기 (!주의)", variable=self.overwrite, fg="red", command=self.toggle_overwrite)
        chk_ow.pack(pady=5, anchor="w")

        # 출력 폴더 지정
        self.btn_out_dir = tk.Button(frame_mid, text="저장 폴더 선택", width=25, command=self.select_output_dir)
        self.btn_out_dir.pack(pady=5)
        
        self.lbl_out_dir = tk.Label(frame_mid, text="원본 폴더에 _pivotfix 추가 저장", fg="gray", wraplength=250)
        self.lbl_out_dir.pack(pady=5)

        # 되돌리기 및 처리 버튼 (하단 고정)
        frame_bottom = tk.Frame(frame_mid)
        frame_bottom.pack(side="bottom", fill="x", pady=10)
        
        self.btn_undo = tk.Button(frame_bottom, text="↩ 되돌리기 (마지막 처리 취소)", width=25, command=self.undo_batch)
        self.btn_undo.pack(pady=(0, 10))
        
        tk.Button(frame_bottom, text="처리 시작", width=25, height=3, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.run_batch).pack()

        # ==========================================
        # 3단: 우측 패널 (미리보기)
        # ==========================================
        frame_right = tk.Frame(self.root, padx=10, pady=10)
        frame_right.pack(side="left", expand=True, fill="both")

        # 미리보기 상단 라벨 묶음
        frame_right_lbls = tk.Frame(frame_right)
        frame_right_lbls.pack(fill="x", pady=(0, 5))
        
        tk.Label(frame_right_lbls, text="[ 원본 캔버스 ]", font=("Arial", 10, "bold")).pack(side="left", expand=True)
        tk.Label(frame_right_lbls, text="[ 2배 확장 + 피봇 보정 후 ]", font=("Arial", 10, "bold")).pack(side="left", expand=True)

        # 캔버스 묶음
        frame_canvases = tk.Frame(frame_right)
        frame_canvases.pack(expand=True, fill="both")
        
        self.canvas_orig = tk.Canvas(frame_canvases, width=260, height=450, bg="#ffffff", relief="sunken", bd=2)
        self.canvas_orig.pack(side="left", padx=(0, 10))
        self.draw_checkerboard(self.canvas_orig, 260, 450)

        self.canvas_res = tk.Canvas(frame_canvases, width=260, height=450, bg="#ffffff", relief="sunken", bd=2)
        self.canvas_res.pack(side="left")
        self.draw_checkerboard(self.canvas_res, 260, 450)

    # ------------------ 기능 메서드 ------------------

    def draw_checkerboard(self, canvas, width, height, size=10):
        for y in range(0, height, size):
            for x in range(0, width, size):
                color = "#ffffff" if ((x//size) + (y//size)) % 2 == 0 else "#dddddd"
                canvas.create_rectangle(x, y, x+size, y+size, fill=color, outline="", tags="checkerboard")
        canvas.tag_lower("checkerboard")

    def toggle_overwrite(self):
        """덮어쓰기 체크 시 폴더 지정 버튼 비활성화, 되돌리기 경고"""
        if self.overwrite.get():
            self.btn_out_dir.config(state="disabled")
            self.btn_undo.config(state="disabled")
            self.lbl_out_dir.config(text="원본 파일에 그대로 덮어씌웁니다.\n(되돌리기 불가!)", fg="red")
        else:
            self.btn_out_dir.config(state="normal")
            self.btn_undo.config(state="normal")
            if self.output_dir:
                self.lbl_out_dir.config(text=self.output_dir, fg="gray")
            else:
                self.lbl_out_dir.config(text="원본 폴더에 _pivotfix 추가 저장", fg="gray")

    def load_files_dialog(self):
        """다중 파일 또는 폴더 선택 통합 다이얼로그 (사용자 편의)"""
        # tkinter는 파일 여러 개 열기가 가능함
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
            messagebox.showwarning("경고", "드롭된 항목 중 PNG 파일이 없습니다.")

    def add_paths_to_list(self, new_paths):
        """리스트박스 및 내부 변수에 경로 추가"""
        for p in new_paths:
            # 중복 방지
            if p not in self.input_paths:
                self.input_paths.append(p)
                self.listbox.insert(tk.END, os.path.basename(p))
                
        self.lbl_input_info.config(text=f"선택된 파일: {len(self.input_paths)}개")
        
        # 첫 추가 시 첫 번째 항목 자동 선택 및 미리보기
        if self.input_paths and not self.preview_path:
            self.listbox.selection_set(0)
            self.preview_path = self.input_paths[0]
            self.update_preview()

    def on_list_select(self, event):
        """리스트 박스 클릭 시 미리보기 변경"""
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.preview_path = self.input_paths[idx]
            self.update_preview()

    def clear_list(self):
        """파일 목록 초기화"""
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
            self.lbl_out_dir.config(text=folder_path, fg="gray")
        else:
            self.output_dir = ""
            self.lbl_out_dir.config(text="원본 폴더에 _pivotfix 추가 저장", fg="gray")

    def get_alpha_bbox(self, img):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img.split()[-1].getbbox()

    def process_image(self, img, offset_y, h_align):
        """새로운 알고리즘: 원본 크기의 2배 캔버스를 강제 생성하고, 피봇에 맞게 Paste"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
            
        W, H = img.size
        bbox = self.get_alpha_bbox(img)
        
        if bbox is None:
            left, upper, right, lower = 0, 0, W, H
        else:
            left, upper, right, lower = bbox

        # 캔버스 크기를 무조건 가로/세로 2배로 확장 (짝수 보장)
        nW = (W * 2) if (W * 2) % 2 == 0 else (W * 2) + 1
        nH = (H * 2) if (H * 2) % 2 == 0 else (H * 2) + 1

        pivot_x = nW // 2
        pivot_y = nH // 2

        # x축 배치 (h_align 값에 따라 다름)
        if h_align:
            # 보이는 영역의 x 중앙
            cx_visible = (left + right) // 2
            paste_x = pivot_x - cx_visible
        else:
            # 원본 이미지의 x 중앙
            paste_x = pivot_x - (W // 2)

        # y축 배치: 보이는 영역의 가장 하단(lower) 픽셀이 피봇 중앙 바로 위에 오도록
        paste_y = pivot_y - lower + offset_y

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
            res_img = self.process_image(img, self.offset_y.get(), self.h_align.get())

            # UI 캔버스 크기: 260x450, 안전한 스케일 한도: 240x430
            img_preview = self.resize_for_preview(img, 240, 430)
            self.tk_orig = ImageTk.PhotoImage(img_preview)
            self.canvas_orig.create_image(130, 225, image=self.tk_orig, anchor="center", tags="preview_image")

            res_preview = self.resize_for_preview(res_img, 240, 430)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(130, 225, image=self.tk_res, anchor="center", tags="preview_image")

            # 2배로 늘어난 결과물 캔버스에서 항상 정중앙이 피봇임
            self.canvas_res.create_line(0, 225, 260, 225, fill="#00e5ff", width=1, tags="crosshair")
            self.canvas_res.create_line(130, 0, 130, 450, fill="#00e5ff", width=1, tags="crosshair")
            
        except Exception as e:
            print(f"미리보기 오류: {e}")

    def run_batch(self):
        if not self.input_paths:
            messagebox.showwarning("경고", "처리할 파일이 없습니다.")
            return

        is_overwrite = self.overwrite.get()
        
        if is_overwrite:
            ans = messagebox.askyesno("경고", "원본 파일을 덮어씁니다. 이 작업은 되돌릴 수 없습니다!\n진행하시겠습니까?")
            if not ans: return

        success_count = 0
        h_align_val = self.h_align.get()
        offset_y_val = self.offset_y.get()

        self.last_generated_files.clear()

        for idx, path in enumerate(self.input_paths):
            try:
                img = Image.open(path)
                res_img = self.process_image(img, offset_y_val, h_align_val)
                
                # 원본 이미지를 안전하게 닫아주어야 덮어쓰기가 가능함
                img.close()
                
                if is_overwrite:
                    save_path = path
                else:
                    basename = os.path.basename(path)
                    name, ext = os.path.splitext(basename)
                    new_filename = f"{name}_pivotfix.png"
                    save_dir = self.output_dir if self.output_dir else os.path.dirname(path)
                    save_path = os.path.join(save_dir, new_filename)
                    self.last_generated_files.append(save_path) # 되돌리기를 위해 경로 저장
                
                res_img.save(save_path, "PNG")
                success_count += 1
            except Exception as e:
                print(f"파일 처리 실패: {path} - {e}")
                
            if idx % 10 == 0:
                self.root.update()

        if is_overwrite:
            messagebox.showinfo("완료", f"총 {success_count}개 파일 덮어쓰기 완료!")
        else:
            messagebox.showinfo("완료", f"총 {len(self.input_paths)}개 중 {success_count}개 파일 처리 완료!")

    def undo_batch(self):
        if self.overwrite.get():
            messagebox.showwarning("경고", "덮어쓰기 모드에서는 되돌리기 기능을 사용할 수 없습니다.")
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
                    print(f"삭제 실패: {path} - {e}")
                    
        self.last_generated_files.clear()
        messagebox.showinfo("되돌리기 완료", f"{count}개의 파일이 성공적으로 삭제되었습니다.")

if __name__ == "__main__":
    try:
        root = TkinterDnD.Tk()
    except Exception as e:
        print("tkinterdnd2 초기화 오류:", e)
        print("requirements.txt의 패키지가 정상적으로 설치되었는지 확인해주세요.")
        root = tk.Tk()
        
    app = PivotFixerApp(root)
    root.mainloop()