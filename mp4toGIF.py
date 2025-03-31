from moviepy.editor import VideoFileClip
from PIL import Image
import os
import shutil
import logging
import sys
import tkinter as tk
from tkinter import ttk
from threading import Thread
from tqdm import tqdm

# 抑制所有日誌輸出
logging.getLogger('moviepy').setLevel(logging.CRITICAL)
if getattr(sys, 'frozen', False):
    # 如果是執行檔模式，設定ffmpeg路徑
    ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
# 重定向標準錯誤輸出
class DevNull:
    def write(self, msg): pass
sys.stderr = DevNull()

def convert_video_to_gif(video_path, output_path, fail_path, resize_factor=1.0, optimize=True):
    try:

        video = VideoFileClip(video_path)

        if video.duration > 15:
            print(f"視頻長度 ({video.duration:.2f}秒) 超過15秒限制，移至fail_files資料夾")
            video.close()
            shutil.copy2(video_path, fail_path)
            return False

        original_fps = video.fps
        target_fps = 20
        if original_fps < 15:
            target_fps = original_fps
            print(f"低幀率視頻，使用原始幀率: {original_fps:.2f} fps")
        else:
            print(f"原始幀率: {original_fps:.2f} fps，使用標準: {target_fps} fps")

        # 強制 RGB、避免首幀損壞
        video = video.set_duration(video.duration).set_fps(target_fps).resize(resize_factor).fl_image(lambda f: f[:, :, :3])

        # 改回 ffmpeg 解決播放緩慢問題
        video.write_gif(
            output_path,
            fps=target_fps,
            program='ffmpeg'
        )

        # 移除前兩幀
        try:
            with Image.open(output_path) as img:
                frames = []
                try:
                    img.seek(2)  # 跳過前兩幀
                    while True:
                        frame = img.copy()
                        duration = img.info.get('duration', 50)
                        frames.append({'image': frame, 'duration': duration})
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass

            if frames:
                frames[0]['image'].save(
                    output_path,
                    save_all=True,
                    append_images=[f['image'] for f in frames[1:]],
                    duration=[f['duration'] for f in frames],
                    loop=0,
                    format='GIF'
                )
                print("已成功刪除前兩幀")
        except Exception as e:
            print(f"移除前兩幀失敗: {e}")

        video.close()
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"轉換完成！幀率: {target_fps} fps，大小: {file_size:.2f} MB")

        with Image.open(output_path) as img:
            width, height = img.size

        if file_size <= 8:
            print(f"GIF文件 {file_size:.2f}MB，直接保存")
            return True

        original_gif = output_path + '.temp'
        shutil.copy2(output_path, original_gif)

        scale = 0.8
        fixed_duration = int(1000 / target_fps)
        while scale >= 0.1:
            print(f"嘗試 {scale*100}% 縮放...")
            try:
                with Image.open(original_gif) as img:
                    frames = []
                    try:
                        while True:
                            new_size = tuple(int(dim * scale) for dim in img.size)
                            resized_frame = img.resize(new_size, Image.Resampling.LANCZOS)
                            frames.append({'image': resized_frame, 'duration': fixed_duration})
                            img.seek(img.tell() + 1)
                    except EOFError:
                        pass

                    temp_output = output_path + '.resize'
                    if frames:
                        frames[0]['image'].save(
                            temp_output,
                            save_all=True,
                            append_images=[f['image'] for f in frames[1:]],
                            duration=[f['duration'] for f in frames],
                            loop=0,
                            format='GIF'
                        )

                new_file_size = os.path.getsize(temp_output) / (1024 * 1024)
                print(f"縮放後大小: {new_size}, 文件: {new_file_size:.2f}MB")

                if new_file_size <= 8:
                    print(f"調整後大小符合：{new_file_size:.2f}MB")
                    os.replace(temp_output, output_path)
                    os.remove(original_gif)
                    return True

                if new_size[0] <= 250 or new_size[1] <= 250:
                    print(f"縮放後尺寸 {new_size} 過小，移至fail")
                    fail_gif_path = fail_path.replace('.mp4', '.gif')
                    shutil.copy2(temp_output, fail_gif_path)
                    os.remove(temp_output)
                    os.remove(original_gif)
                    os.remove(output_path)
                    return False

                os.remove(temp_output)
            except Exception as e:
                print(f"縮放錯誤: {str(e)}")
                for temp_file in [temp_output, original_gif]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                raise

            scale = round(scale - 0.1, 1)

        if os.path.exists(original_gif):
            os.remove(original_gif)

        print(f"轉換完成! GIF已保存: {output_path}")

    except Exception as e:
        print(f"轉換錯誤: {str(e)}")


class ConversionGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MP4 轉 GIF 轉換器")
        self.root.geometry("600x400")
        
        # 檢查必要資料夾
        self.input_folder = "mp4_files"
        self.output_folder = "gif_files"
        self.fail_folder = "fail_files"
        
        # 創建必要的資料夾
        try:
            for folder in [self.input_folder, self.output_folder, self.fail_folder]:
                if not os.path.exists(folder):
                    os.makedirs(folder)
        except Exception as e:
            tk.messagebox.showerror("錯誤", f"創建資料夾時發生錯誤：{str(e)}")
            self.force_quit()
        
        # 設置關閉視窗事件處理
        self.root.protocol("WM_DELETE_WINDOW", self.force_quit)
        
        # 配置根窗口的網格權重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 創建主框架
        self.main_frame = ttk.Frame(self.root, padding="30")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置主框架的網格權重
        self.main_frame.grid_columnconfigure(0, weight=1)
        for i in range(4):
            self.main_frame.grid_rowconfigure(i, weight=1)
        
        # 狀態標籤
        self.status_label = ttk.Label(
            self.main_frame,
            text="準備開始轉換...",
            font=("微軟正黑體", 12)
        )
        self.status_label.grid(row=0, column=0, pady=(20,10), sticky="n")
        
        # 進度條
        self.progress = ttk.Progressbar(
            self.main_frame, 
            orient="horizontal",
            length=450,
            mode="determinate"
        )
        self.progress.grid(row=1, column=0, pady=20, sticky="ew")
        
        # 詳細資訊標籤
        self.info_label = ttk.Label(
            self.main_frame,
            text="",
            font=("微軟正黑體", 10)
        )
        self.info_label.grid(row=2, column=0, pady=20, sticky="n")
        
        # 創建按鈕框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=3, column=0, pady=(20,30), sticky="s")
        
        # 開始按鈕
        self.start_button = ttk.Button(
            button_frame,
            text="開始轉換",
            command=self.start_conversion,
            width=15
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        # 取消按鈕
        self.cancel_button = ttk.Button(
            button_frame,
            text="取消轉換",
            command=self.cancel_conversion,
            width=15,
            state="disabled"
        )
        self.cancel_button.grid(row=0, column=1, padx=5)
        
        self.is_converting = False
        self.should_cancel = False
        
        # 設置視窗樣式
        style = ttk.Style()
        style.configure("TButton", padding=5, font=("微軟正黑體", 10))
        style.configure("TLabel", font=("微軟正黑體", 10))
        
        # 讓視窗在螢幕中央顯示
        self.center_window()
    
    def force_quit(self):
        """強制結束程式"""
        if self.is_converting:
            self.should_cancel = True
        self.root.quit()
        self.root.destroy()
        os._exit(0)  # 強制結束程式
    
    def cancel_conversion(self):
        """取消轉換過程"""
        self.should_cancel = True
        self.cancel_button["state"] = "disabled"
        self.status_label["text"] = "正在取消轉換..."
    
    def start_conversion(self):
        if self.is_converting:
            return
        
        self.is_converting = True
        self.should_cancel = False
        self.start_button["state"] = "disabled"
        self.cancel_button["state"] = "normal"
        Thread(target=self.conversion_process).start()
    
    def conversion_process(self):
        try:
            # 檢查輸入資料夾是否存在
            if not os.path.exists(self.input_folder):
                self.status_label["text"] = f"找不到輸入資料夾：{self.input_folder}"
                return
            
            # 獲取所有MP4文件
            mp4_files = [f for f in os.listdir(self.input_folder) if f.endswith('.mp4')]
            
            if not mp4_files:
                self.status_label["text"] = f"在 {self.input_folder} 中沒有找到MP4文件"
                self.is_converting = False
                self.start_button["state"] = "normal"
                self.cancel_button["state"] = "disabled"
                return
            
            total_files = len(mp4_files)
            self.status_label["text"] = f"找到 {total_files} 個文件，開始轉換..."
            
            # 處理每個文件
            for index, mp4_file in enumerate(mp4_files, 1):
                if self.should_cancel:
                    self.status_label["text"] = "轉換已取消"
                    break
                
                try:
                    video_path = os.path.join(self.input_folder, mp4_file)
                    output_path = os.path.join(self.output_folder, mp4_file.replace('.mp4', '.gif'))
                    fail_path = os.path.join(self.fail_folder, mp4_file)
                    
                    self.update_progress(index, total_files, f"正在處理: {mp4_file}")
                    
                    if not os.path.exists(video_path):
                        print(f"找不到文件：{video_path}")
                        continue
                    
                    convert_video_to_gif(video_path, output_path, fail_path)
                    
                except Exception as e:
                    print(f"處理文件 {mp4_file} 時發生錯誤: {str(e)}")
                    continue
            
            if not self.should_cancel:
                self.status_label["text"] = "轉換完成！"
            
        except Exception as e:
            self.status_label["text"] = f"發生錯誤: {str(e)}"
            print(f"轉換過程中發生錯誤: {str(e)}")
        finally:
            self.is_converting = False
            self.should_cancel = False
            self.start_button["state"] = "normal"
            self.cancel_button["state"] = "disabled"
    
    def update_progress(self, current, total, message=""):
        progress = (current / total) * 100
        self.progress["value"] = progress
        self.info_label["text"] = f"處理進度: {current}/{total} ({progress:.1f}%)\n{message}"
        self.root.update()
    
    def center_window(self):
        """將視窗置中於螢幕"""
        try:
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except Exception as e:
            print(f"置中視窗時發生錯誤: {str(e)}")

    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"運行程式時發生錯誤: {str(e)}")
            self.force_quit()

if __name__ == "__main__":
    app = ConversionGUI()
    app.run()
