import aiohttp
import asyncio
import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import pyperclip
import webbrowser
from PIL import Image
from io import BytesIO

CONFIG_FILE = "downloader_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"download_path": os.path.join(os.path.expanduser("~"), "Downloads", "discord_media")}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except:
        pass

config = load_config()
DOWNLOAD_PATH = config.get(
    "download_path", 
    os.path.join(os.path.expanduser("~"), "Downloads", "discord_media")
)
Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

async def download_file(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
            raise Exception(f"HTTP {resp.status}")

def save_image(data, path, convert_to_png=False):
    try:
        if convert_to_png:
            img = Image.open(BytesIO(data)).convert("RGBA")
            img.save(path, "PNG")
        else:
            with open(path, "wb") as f:
                f.write(data)
        return True
    except Exception as e:
        print(f"Error saving image: {e}")
        return False

async def download_single_sticker(sticker_id, save_path, status_cb):
    url = f"https://media.discordapp.net/stickers/{sticker_id}.png?size=160"
    
    try:
        data = await download_file(url)
        if save_image(data, save_path, convert_to_png=True):
            status_cb(f"Sticker saved: {save_path}")
            return True
    except Exception as e:
        status_cb(f"Error: {e}")
    return False

async def download_single_emoji(emoji_id, save_path_png, save_path_gif, url_var, status_cb):
    url_gif = f"https://cdn.discordapp.com/emojis/{emoji_id}.gif?size=48"
    url_png = f"https://cdn.discordapp.com/emojis/{emoji_id}.png?size=48"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url_gif) as r1:
                if r1.status == 200:
                    data = await r1.read()
                    save_image(data, save_path_gif)
                    url_var.set(url_gif)
                    status_cb(f"Emoji saved: {save_path_gif}")
                    return True
            
            async with session.get(url_png) as r2:
                if r2.status == 200:
                    data = await r2.read()
                    save_image(data, save_path_png, convert_to_png=True)
                    url_var.set(url_png)
                    status_cb(f"Emoji saved: {save_path_png}")
                    return True
    except Exception as e:
        status_cb(f"Error: {e}")
    
    return False

class DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Media Downloader")
        self.root.geometry("750x600")
        self.root.resizable(False, False)
        self.setup_ui()

    def setup_ui(self):
        main = tk.Frame(self.root, padx=15, pady=15)
        main.pack(fill="both", expand=True)
        
        tk.Label(main, text="Discord Media Downloader", 
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))
        
        path_frame = tk.Frame(main)
        path_frame.pack(fill="x", pady=(0, 20))
        tk.Label(path_frame, text="Download folder:").pack(side="left")
        self.path_var = tk.StringVar(value=DOWNLOAD_PATH)
        tk.Entry(path_frame, textvariable=self.path_var, width=50, state="readonly").pack(side="left", padx=10)
        tk.Button(path_frame, text="Change", command=self.change_path).pack(side="left")
        
        tk.Frame(main, height=2, bg="#ccc").pack(fill="x", pady=15)
        
        sticker_frame = tk.LabelFrame(main, text="Download Sticker by ID (128×128)", padx=15, pady=15)
        sticker_frame.pack(fill="x")
        row = tk.Frame(sticker_frame)
        row.pack(fill="x")
        tk.Label(row, text="Sticker ID:").pack(side="left")
        self.sticker_entry = tk.Entry(row, width=40)
        self.sticker_entry.pack(side="left", padx=10)
        tk.Button(row, text="Download", command=self.download_sticker).pack(side="left")
        self.sticker_url_var = tk.StringVar()
        tk.Entry(sticker_frame, textvariable=self.sticker_url_var, state="readonly", width=70).pack(pady=8)
        btns = tk.Frame(sticker_frame)
        btns.pack()
        tk.Button(btns, text="Copy URL", command=lambda: self.copy_to_clip(self.sticker_url_var.get())).pack(side="left", padx=5)
        tk.Button(btns, text="Open in browser", command=lambda: self.open_url(self.sticker_url_var.get())).pack(side="left", padx=5)
        
        tk.Frame(main, height=2, bg="#ccc").pack(fill="x", pady=15)
        
        emoji_frame = tk.LabelFrame(main, text="Download Emoji by ID (48×48)", padx=15, pady=15)
        emoji_frame.pack(fill="x")
        row2 = tk.Frame(emoji_frame)
        row2.pack(fill="x")
        tk.Label(row2, text="Emoji ID:").pack(side="left")
        self.emoji_entry = tk.Entry(row2, width=40)
        self.emoji_entry.pack(side="left", padx=10)
        tk.Button(row2, text="Download", command=self.download_emoji).pack(side="left")
        self.emoji_url_var = tk.StringVar()
        tk.Entry(emoji_frame, textvariable=self.emoji_url_var, state="readonly", width=70).pack(pady=8)
        btns2 = tk.Frame(emoji_frame)
        btns2.pack()
        tk.Button(btns2, text="Copy URL", command=lambda: self.copy_to_clip(self.emoji_url_var.get())).pack(side="left", padx=5)
        tk.Button(btns2, text="Open in browser", command=lambda: self.open_url(self.emoji_url_var.get())).pack(side="left", padx=5)
        
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(main, textvariable=self.status_var, fg="#666").pack(pady=10)

    def change_path(self):
        global DOWNLOAD_PATH
        new = filedialog.askdirectory(initialdir=DOWNLOAD_PATH)
        if new:
            DOWNLOAD_PATH = new
            self.path_var.set(new)
            config["download_path"] = new
            save_config(config)
            self.set_status(f"Folder changed to: {new}")

    def download_sticker(self):
        sid = self.sticker_entry.get().strip()
        if not sid.isdigit():
            messagebox.showerror("Error", "Invalid ID")
            return
        
        save_path = os.path.join(DOWNLOAD_PATH, f"sticker_{sid}.png")
        self.sticker_url_var.set(f"https://media.discordapp.net/stickers/{sid}.png?size=128")
        
        async def task():
            ok = await download_single_sticker(sid, save_path, self.set_status)
            if ok:
                messagebox.showinfo("Success", f"Sticker saved to:\n{save_path}")
        
        asyncio.run(task())

    def download_emoji(self):
        eid = self.emoji_entry.get().strip()
        if not eid.isdigit():
            messagebox.showerror("Error", "Invalid ID")
            return
        
        save_png = os.path.join(DOWNLOAD_PATH, f"emoji_{eid}.png")
        save_gif = os.path.join(DOWNLOAD_PATH, f"emoji_{eid}.gif")
        
        async def task():
            ok = await download_single_emoji(
                eid, save_png, save_gif, self.emoji_url_var, self.set_status
            )
            if ok:
                messagebox.showinfo("Success", "Emoji downloaded successfully")
            else:
                messagebox.showerror("Error", "Failed to download emoji")
        
        asyncio.run(task())

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def copy_to_clip(self, text):
        if text:
            pyperclip.copy(text)
            self.set_status("URL copied to clipboard")

    def open_url(self, url):
        if url:
            webbrowser.open(url)

def main():
    root = tk.Tk()
    DownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()