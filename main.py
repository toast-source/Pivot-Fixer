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
        self.root.geometry("950x500")
        self.root.resizable(False, False)

        # 드래그 앤 드롭 설정
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        self.input_paths = []
        self.preview_path = None
        self.output_dir = ""
        self.last_generated_files = [] # 되돌리기(Undo)를 위한 최근 생성 파일 목록

        # 세로 이동 값: 0 ~ 6 px
        self.offset_y = tk.IntVar(value=0)
        # 좌우 중앙 정렬 여부
        self.h_align = tk.BooleanVar(value=True)

        self.tk_orig = None
        self.tk_res = None

        self.setup_ui()

    def setup_ui(self):
        # ---------------- 좌측 패널 (컨트롤) ----------------
        frame_ctrl = tk.Frame(self.root, padx=10, pady=10, width=250)
        frame_ctrl.pack(side="left", fill="y")
        frame_ctrl.pack_propagate(False)

        tk.Label(frame_ctrl, text="[ 파일 선택 ]", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        tk.Label(frame_ctrl, text="여기로 파일/폴더를 드래그 하세요", fg="gray", font=("Arial", 9)).pack(pady=(0, 5))
        tk.Button(frame_ctrl, text="PNG 단일 파일 열기", width=25, command=self.load_single_file).pack(pady=2)
        tk.Button(frame_ctrl, text="폴더 열기 (일괄 처리)", width=25, command=self.load_folder).pack(pady=2)
        
        self.lbl_input_info = tk.Label(frame_ctrl, text="선택된 파일: 0개", fg="blue")
        self.lbl_input_info.pack(pady=5)

        tk.Label(frame_ctrl, text="[ 설정 ]", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        
        frame_y = tk.Frame(frame_ctrl)
        frame_y.pack(pady=2)
        tk.Label(frame_y, text="세로 보정값 (px):").pack(side="left")
        
        # 0 ~ 6 까지 선택 가능한 Combobox
        cb_y = ttk.Combobox(frame_y, textvariable=self.offset_y, values=[0, 1, 2, 3, 4, 5, 6], state="readonly", width=5)
        cb_y.pack(side="left", padx=5)
        cb_y.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        chk_h = tk.Checkbutton(frame_ctrl, text="좌우 피봇 보정 (보이는 영역 중앙정렬)", variable=self.h_align, command=self.update_preview)
        chk_h.pack(pady=2)

        tk.Label(frame_ctrl, text="[ 출력 위치 ]", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        tk.Button(frame_ctrl, text="저장 폴더 선택", width=25, command=self.select_output_dir).pack(pady=2)
        self.lbl_out_dir = tk.Label(frame_ctrl, text="원본 폴더에 저장", fg="gray", wraplength=230)
        self.lbl_out_dir.pack(pady=5)

        # 되돌리기 및 처리 버튼
        frame_bottom = tk.Frame(frame_ctrl)
        frame_bottom.pack(side="bottom", fill="x", pady=10)
        
        tk.Button(frame_bottom, text="↩ 되돌리기 (마지막 처리 취소)", width=25, command=self.undo_batch).pack(pady=(0, 5))
        tk.Button(frame_bottom, text="처리 시작", width=25, height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.run_batch).pack()
        
        # ---------------- 중앙 패널 (원본 미리보기) ----------------
        frame_orig = tk.Frame(self.root, padx=10, pady=10)
        frame_orig.pack(side="left", expand=True, fill="both")
        tk.Label(frame_orig, text="원본 미리보기", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        
        # 캔버스 크기를 300x400으로 키워 이미지가 경계선에 잘리는 현상 방지
        self.canvas_orig = tk.Canvas(frame_orig, width=300, height=400, bg="#ffffff", relief="sunken", bd=2)
        self.canvas_orig.pack()
        self.draw_checkerboard(self.canvas_orig, 300, 400)

        # ---------------- 우측 패널 (결과 미리보기) ----------------
        frame_res = tk.Frame(self.root, padx=10, pady=10)
        frame_res.pack(side="left", expand=True, fill="both")
        tk.Label(frame_res, text="처리 후 미리보기 (십자선: 최종 중심)", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        self.canvas_res = tk.Canvas(frame_res, width=300, height=400, bg="#ffffff", relief="sunken", bd=2)
        self.canvas_res.pack()
        self.draw_checkerboard(self.canvas_res, 300, 400)

    def draw_checkerboard(self, canvas, width, height, size=10):
        """투명도를 시각적으로 보여주는 체커보드 배경 그리기"""
        for y in range(0, height, size):
            for x in range(0, width, size):
                color = "#ffffff" if ((x//size) + (y//size)) % 2 == 0 else "#dddddd"
                canvas.create_rectangle(x, y, x+size, y+size, fill=color, outline="", tags="checkerboard")
        canvas.tag_lower("checkerboard")

    def on_drop(self, event):
        """파일 또는 폴더를 드래그 앤 드롭 했을 때 처리"""
        paths = self.root.tk.splitlist(event.data)
        if not paths: return
        
        png_files = []
        for p in paths:
            if os.path.isdir(p):
                png_files.extend(glob.glob(os.path.join(p, "*.png")))
            elif p.lower().endswith(".png"):
                png_files.append(p)
        
        if png_files:
            self.input_paths = png_files
            self.preview_path = png_files[0]
            self.lbl_input_info.config(text=f"선택된 파일: {len(self.input_paths)}개")
            self.update_preview()
        else:
            messagebox.showwarning("경고", "드롭된 항목 중 PNG 파일이 없습니다.")

    def load_single_file(self):
        """단일 파일 선택"""
        file_path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if file_path:
            self.input_paths = [file_path]
            self.preview_path = file_path
            self.lbl_input_info.config(text="선택된 파일: 1개")
            self.update_preview()

    def load_folder(self):
        """폴더 내의 PNG 일괄 선택"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_paths = glob.glob(os.path.join(folder_path, "*.png"))
            if not self.input_paths:
                messagebox.showwarning("경고", "해당 폴더에 PNG 파일이 없습니다.")
                self.lbl_input_info.config(text="선택된 파일: 0개")
                self.preview_path = None
            else:
                self.lbl_input_info.config(text=f"선택된 파일: {len(self.input_paths)}개")
                self.preview_path = self.input_paths[0]
            self.update_preview()

    def select_output_dir(self):
        """출력 폴더 선택"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_dir = folder_path
            self.lbl_out_dir.config(text=folder_path)
        else:
            self.output_dir = ""
            self.lbl_out_dir.config(text="원본 폴더에 저장")

    def get_alpha_bbox(self, img):
        """이미지에서 실제 투명하지 않은 픽셀의 Bounding Box 추출"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img.split()[-1].getbbox()

    def process_image(self, img, offset_y, h_align):
        """보정 알고리즘: 이미지의 픽셀을 자르지 않고 투명 캔버스를 확장하여 중심점(피봇)을 보정합니다."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
            
        W, H = img.size
        bbox = self.get_alpha_bbox(img)
        
        if bbox is None:
            left, upper, right, lower = 0, 0, W, H
        else:
            left, upper, right, lower = bbox

        pad_left, pad_right = 0, 0
        if h_align:
            Dx = W - (left + right)
            if Dx > 0:
                pad_left = Dx
                pad_right = 0
            else:
                pad_left = 0
                pad_right = -Dx

        # 세로 정렬: 기존 이미지 데이터의 가장 하단 픽셀이 새 캔버스 중앙 피봇 바로 위에 위치하도록 계산
        # 수식: Dy = 원본 높이 - 2 * 보이는 영역 하단 좌표(lower) + 2 * offset_y
        Dy = H - 2 * lower + 2 * offset_y
        pad_top, pad_bottom = 0, 0
        if Dy > 0:
            pad_top = Dy
            pad_bottom = 0
        else:
            pad_top = 0
            pad_bottom = -Dy

        nW = W + pad_left + pad_right
        nH = H + pad_top + pad_bottom

        new_img = Image.new("RGBA", (nW, nH), (0, 0, 0, 0))
        new_img.paste(img, (pad_left, pad_top))
        return new_img

    def resize_for_preview(self, img, max_w, max_h):
        """픽셀 아트용 스케일링: 정수 배율을 지향하되 비율 유지, 확대 시 Nearest 보간법 사용"""
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        
        if ratio >= 1:
            ratio = int(ratio) # 픽셀이 부분적으로 찌그러지는 현상을 막기 위해 정수 배율 강제
            
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        
        return img.resize((new_w, new_h), Image.Resampling.NEAREST)

    def update_preview(self):
        """설정 변경 시 미리보기 화면 업데이트"""
        self.canvas_orig.delete("preview_image")
        self.canvas_res.delete("preview_image")
        self.canvas_res.delete("crosshair")
        
        if not self.preview_path or not os.path.exists(self.preview_path):
            return

        try:
            # 원본 이미지
            img = Image.open(self.preview_path).convert("RGBA")
            # 보정된 이미지
            res_img = self.process_image(img, self.offset_y.get(), self.h_align.get())

            # 1. 원본 미리보기 스케일링 (최대 280x380, 캔버스는 300x400이므로 10px씩 여유가 생김)
            img_preview = self.resize_for_preview(img, 280, 380)
            self.tk_orig = ImageTk.PhotoImage(img_preview)
            self.canvas_orig.create_image(150, 200, image=self.tk_orig, anchor="center", tags="preview_image")

            # 2. 결과 미리보기 스케일링
            res_preview = self.resize_for_preview(res_img, 280, 380)
            self.tk_res = ImageTk.PhotoImage(res_preview)
            self.canvas_res.create_image(150, 200, image=self.tk_res, anchor="center", tags="preview_image")

            # 3. 얇고 뚜렷한 십자선 그리기 (색상: 눈에 띄는 Cyan 시안색, 두께 1px)
            # 피봇을 정확히 나타내기 위해 점선을 없애고 실선으로 표현
            self.canvas_res.create_line(0, 200, 300, 200, fill="#00e5ff", width=1, tags="crosshair")
            self.canvas_res.create_line(150, 0, 150, 400, fill="#00e5ff", width=1, tags="crosshair")
            
        except Exception as e:
            print(f"미리보기 오류: {e}")

    def run_batch(self):
        """선택된 파일(들) 일괄 처리"""
        if not self.input_paths:
            messagebox.showwarning("경고", "처리할 파일이 없습니다.")
            return

        success_count = 0
        h_align_val = self.h_align.get()
        offset_y_val = self.offset_y.get()

        # 새로운 처리가 시작되므로 이전 파일 리스트 초기화
        self.last_generated_files.clear()

        for idx, path in enumerate(self.input_paths):
            try:
                img = Image.open(path)
                res_img = self.process_image(img, offset_y_val, h_align_val)
                
                basename = os.path.basename(path)
                name, ext = os.path.splitext(basename)
                new_filename = f"{name}_pivotfix.png"
                
                save_dir = self.output_dir if self.output_dir else os.path.dirname(path)
                save_path = os.path.join(save_dir, new_filename)
                
                res_img.save(save_path, "PNG")
                self.last_generated_files.append(save_path) # 되돌리기를 위해 경로 저장
                success_count += 1
            except Exception as e:
                print(f"파일 처리 실패: {path} - {e}")
                
            if idx % 10 == 0:
                self.root.update()

        messagebox.showinfo("완료", f"총 {len(self.input_paths)}개 중 {success_count}개 파일 처리 완료!")

    def undo_batch(self):
        """마지막 일괄 처리로 생성된 파일들을 삭제(되돌리기)"""
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
        # 만약 DND 모듈이 설치되지 않았다면 일반 Tk()로 폴백(fallback)하여 실행
        root = tk.Tk()
        
    app = PivotFixerApp(root)
    root.mainloop()