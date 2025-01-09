import requests
import os
import tkinter as mp4togif
from bs4 import BeautifulSoup
import threading
import re

urls = []
lock = threading.Lock()
counter = 0

#判斷檔案大小是否小於5MiB
def filesizecompare(number):
    if number.endswith('MiB'):
        number = float(number[:-3])
        print(number)
        if number >= 10.0:
            return True
        else:
            return False
    elif number.endswith('KiB'):
        return False
    else:
        return True



def submit_input():
    input_text = input_var.get()
    input_var.set("")
    if input_text != "":
        # 檢查是否為圖片檔
        pattern = r'\.(png|jpg|jpeg|bmp|tiff|gif)(\?|$)'
        if re.search(pattern, input_text, re.IGNORECASE):
            print("圖片檔被跳過:", input_text)
            return
        with lock:
            urls.append(input_text)  # 加入新的網址
            label_urls.config(text="\n".join(urls))
            form_data = {
                # 要轉乘gif的mp4的網址
                'new-image-url': urls[0],
                'upload': 'Upload video!'
            }
            # 發送POST請求
            response = requests.post(
                'https://ezgif.com/video-to-gif', data=form_data)

            # 解析HTML頁面，獲取返回的URL
            url = response.url
            response = requests.post(url)
            # 輸出mp4 to gif網址
            print(url) #印出mp4輸入的網址

            # 進入mp4 to gif頁面
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            mp4size = 'original'
            #尋找width值
            filestats_text = soup.find('div', {'id': 'main'}).find('p', class_='filestats').text
            # 使用正则表达式提取width值
            width_match = re.search(r'width: (\d+px)', filestats_text)
            if width_match:
                print(width_match.group(0))
                # 使用正则表达式从字符串中提取数字
                match = re.search(r'(\d+)px', width_match.group(0))
                if int(match.group(1)) <= 600:
                    mp4size = 'original'
                else:
                    mp4size = '480'
            else:
                print("Width not found")
                
            form = soup.find('form', {'class': 'ajax-form'})
            # 輸入所需要的data資料
            data = {
                'file': form.find('input', {'name': 'file'})['value'],
                'start': '0',
                'end': form.find('input', {'name': 'end'})['value'],
                'size': mp4size,
                'fps': '20',
                'method': 'ffmpeg',
                'diff': ''
            }
            # 將data送出 將mp4轉成gif
            response = requests.post(url, data=data)

            # 尋找變成gif後的網址
            soup = BeautifulSoup(response.text, 'html.parser')
            output_div = soup.find('div', {'id': 'output'})
            td_tags = output_div.find_all('td')
            for td in td_tags:
                if td.find('a', {'title': 'Compress image'}):
                    url = td.find('a')['href']

            # 輸出轉換mp4togif完成的網址
            # 檢查url是否以"https://"開頭
            if not url.startswith("https://"):
                url = "https://ezgif.com/" + url
            print(url)
            filename = os.path.basename(url)
            lossynumber = 40
            size = soup.find('div', {'id': 'output'}).find('strong').text
            while filesizecompare(size) and lossynumber < 201:
                # 開始optimize
                data = {
                    'file': filename,
                    'method': 'gifsicle',
                    'lossy': lossynumber
                }

                response = requests.post(url, data=data)

                # 檢查是否有正常優化
                soup = BeautifulSoup(response.text, 'html.parser')

                # 尋找optimize後的檔案大小
                size = soup.find('div', {'id': 'output'}).find('strong').text
                lossynumber = lossynumber + 40

            # 尋找optimize完的下載網址
            soup = BeautifulSoup(response.text, 'html.parser')
            output_div = soup.find('div', {'id': 'output'})
            td_tags = output_div.find_all('td')
            for td in td_tags:
                if td.find('a', {'class': 'save'}):
                    url = td.find('a')['href']

            # 輸出轉換mp4togif完成的網址
                
            # 檢查url是否以"https://"開頭
            if not url.startswith("https://"):
                url = "https://ezgif.com/" + url
            print(url)

            # 下載到本機
            filename = 'C:\\Users\KH\Desktop\\資料夾\\Hololive中繼站\\hololive暫存\\' + \
                os.path.basename(url)
            response = requests.get(url)
            with open(filename, "wb") as f:
                f.write(response.content)
            urls.pop(0)


def cancel_input():
    root.destroy()


root = mp4togif.Tk()

input_var = mp4togif.StringVar()
input_entry = mp4togif.Entry(root, textvariable=input_var)
input_entry.config(width=50, font=('Arial', 14))
input_entry.pack()

# 建立Label物件
label_urls = mp4togif.Label(root, text="")
# 顯示Label
label_urls.pack()

def run_submit_input(event=None):
    t = threading.Thread(target=submit_input)
    t.start()

submit_button = mp4togif.Button(root, text="送出", command=run_submit_input, default=mp4togif.ACTIVE)
#增加鍵盤enter也可以送出
input_entry.bind('<Return>', run_submit_input)
submit_button.pack()

cancel_button = mp4togif.Button(root, text="取消", command=cancel_input)
cancel_button.pack()

root.title("Mp4 to GIF")
root.geometry("600x150")
root.mainloop()
