import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import os
import platform
import subprocess
import threading
from pathlib import Path


# --- Cross-Platform Downloads Folder Function ---
def get_download_folder():
    """Determines the cross-platform default Downloads folder path."""
    if platform.system() == "Windows":
        try:
            import winreg
            sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                return Path(winreg.QueryValueEx(key, downloads_guid)[0])
        except Exception:
            return Path.home() / "Downloads"
    else:
        return Path.home() / "Downloads"


# --- Downloader Application Class ---
class MediaDownloaderApp:
    def __init__(self, master):
        self.master = master
        master.title("Universal YouTube Downloader")
        master.geometry("550x550")

        self.download_dir = get_download_folder()
        self.audio_quality_options = ["320k (Best)", "192k (Standard)", "128k (Good)"]
        self.video_quality_options = ["2160p (4K)", "1440p (2K)", "1080p (FHD)", "720p (HD)", "480p (SD)"]

        # Tkinter Variables
        self.download_mode_var = tk.StringVar(value="audio")  # 'audio' or 'video'
        self.input_mode_var = tk.StringVar(value="single")  # 'single' or 'playlist'
        self.quality_var = tk.StringVar(value=self.audio_quality_options[0])
        self.status_var = tk.StringVar(value="Ready")

        # List to hold dynamic URL entry widgets
        self.url_entries = []

        self.create_widgets()

    def create_widgets(self):
        # --- 1. DOWNLOAD TYPE (Audio/Video) ---
        type_frame = ttk.LabelFrame(self.master, text="Download Type")
        type_frame.pack(pady=10, padx=10, fill='x')

        ttk.Radiobutton(type_frame, text="Audio (MP3)", variable=self.download_mode_var, value="audio",
                        command=self.update_quality_options).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="Video (MP4)", variable=self.download_mode_var, value="video",
                        command=self.update_quality_options).pack(side=tk.LEFT, padx=10)

        # --- 2. INPUT MODE (Single/Playlist) ---
        input_frame = ttk.LabelFrame(self.master, text="Input Mode")
        input_frame.pack(pady=5, padx=10, fill='x')

        ttk.Radiobutton(input_frame, text="Single Song(s) / Batch URL", variable=self.input_mode_var, value="single",
                        command=self.update_input_fields).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(input_frame, text="Entire Playlist/Channel", variable=self.input_mode_var, value="playlist",
                        command=self.update_input_fields).pack(side=tk.LEFT, padx=10)

        # --- 3. INPUT FIELDS (Dynamic URL Section) ---
        self.input_container = ttk.Frame(self.master)
        self.input_container.pack(pady=5, padx=10, fill='x')
        self.update_input_fields()

        # --- 4. QUALITY SELECTION ---
        quality_frame = ttk.Frame(self.master)
        quality_frame.pack(pady=10, padx=10)

        ttk.Label(quality_frame, text="Quality:").pack(side=tk.LEFT, padx=5)
        self.quality_menu = ttk.OptionMenu(quality_frame, self.quality_var, self.quality_var.get(),
                                           *self.audio_quality_options)
        self.quality_menu.pack(side=tk.LEFT, padx=5)

        # --- 5. ACTION & STATUS ---
        self.download_button = ttk.Button(self.master, text="Start Download", command=self.start_download_thread)
        self.download_button.pack(pady=15)

        ttk.Label(self.master, textvariable=self.status_var).pack(pady=5)
        ttk.Label(self.master, text=f"Output Folder: {self.download_dir.name}").pack()

    # --- GUI Update Methods ---

    def update_quality_options(self):
        """Updates the dropdown menu based on the selected download mode (audio/video)."""
        mode = self.download_mode_var.get()
        options = self.video_quality_options if mode == "video" else self.audio_quality_options

        # Reset variable and update the option menu
        self.quality_var.set(options[0])
        menu = self.quality_menu["menu"]
        menu.delete(0, "end")
        for item in options:
            menu.add_command(label=item, command=tk._setit(self.quality_var, item))

    def update_input_fields(self):
        """Rebuilds the URL input section based on the selected input mode."""
        # Clear existing entries/widgets
        for widget in self.input_container.winfo_children():
            widget.destroy()
        self.url_entries = []

        if self.input_mode_var.get() == "single":
            # Start with one entry box for single/batch mode
            self.add_url_entry()
            ttk.Label(self.input_container, text="Paste URLs one by one:").pack(anchor='w', pady=(5, 0), padx=5)
        else:  # playlist mode
            # Use a single entry box for playlist/channel URL
            var = tk.StringVar()
            entry = ttk.Entry(self.input_container, textvariable=var, width=80)
            entry.pack(pady=5, padx=5, fill='x')
            self.url_entries.append(var)
            ttk.Label(self.input_container, text="Paste single Playlist/Channel URL:").pack(anchor='w', pady=(5, 0),
                                                                                            padx=5)

    def add_url_entry(self, *args):
        """Dynamically adds a new URL input box when the last one is edited."""
        # Only add a new box if the last box is not empty AND it's not the same as the current text
        if self.url_entries and self.url_entries[-1].get().strip() == "":
            return  # Don't add a new box if the last one is empty

        var = tk.StringVar()
        entry = ttk.Entry(self.input_container, textvariable=var, width=80)
        entry.pack(pady=5, padx=5, fill='x')

        # Bind the '<KeyRelease>' event to the entry box to trigger dynamic creation
        entry.bind('<KeyRelease>', self.add_url_entry)
        self.url_entries.append(var)
        self.master.update_idletasks()  # Refresh the GUI immediately

    # --- Downloader Execution Methods ---

    def start_download_thread(self):
        """Collects all URLs and starts the download process in a separate thread."""

        # 1. Collect URLs
        urls = [v.get().strip() for v in self.url_entries]
        urls = [url for url in urls if url]  # Filter out empty entries

        if not urls:
            messagebox.showerror("Error", "Please enter at least one URL.")
            return

        # 2. Disable UI and Update Status
        self.download_button.config(state=tk.DISABLED)
        self.status_var.set(f"Starting download of {len(urls)} item(s)...")

        # 3. Start thread
        download_thread = threading.Thread(target=self.download_media, args=(urls,))
        download_thread.start()

    def download_media(self, urls):
        """Core download logic using yt-dlp."""
        mode = self.download_mode_var.get()  # 'audio' or 'video'
        is_playlist = self.input_mode_var.get() == "playlist"
        selected_quality = self.quality_var.get().split(' ')[0]

        try:
            # Check for FFmpeg installation (Crucial for all post-processing)
            subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.master.after(0, lambda: messagebox.showerror("Error",
                                                              "FFmpeg is required but not found. Please install FFmpeg and ensure it's in your system's PATH."))
            self.master.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.status_var.set("Error: FFmpeg not found")
            return

        # --- yt-dlp Options Configuration ---
        ydl_opts = {
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'keep_intermediate_files': False,
            'ignoreerrors': True,  # Skip videos that fail
            'progress_hooks': [self.hook],
            'noplaylist': not is_playlist,  # True for single/batch mode, False for playlist mode
        }

        if mode == "audio":
            # AUDIO MODE: Extract MP3
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': selected_quality,
                }],
            })

        else:  # Video mode
            # VIDEO MODE: Download best video + best audio and merge (requires FFmpeg)
            # Example format string based on resolution:
            # 'bestvideo[height<=1080]+bestaudio/best'

            # Extract target resolution number (e.g., 1080 from 1080p)
            target_res = int(selected_quality.replace('p', ''))

            ydl_opts.update({
                # This complex format string selects the best video stream up to the target resolution
                # and pairs it with the best audio stream, then merges them.
                'format': f'bestvideo[height<={target_res}]+bestaudio/best',
            })
            # Note: FFmpeg is used automatically by yt-dlp for merging video and audio

        # --- Execute Download ---
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)

            self.master.after(0, lambda: self.status_var.set(f"Download Complete! Saved to {self.download_dir.name}"))
            self.master.after(0, lambda: messagebox.showinfo("Success",
                                                             f"All media downloaded successfully to: {self.download_dir}"))

        except Exception as e:
            self.master.after(0, lambda: self.status_var.set(f"Error: {e}"))
            self.master.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {e}"))

        finally:
            self.master.after(0, lambda: self.download_button.config(state=tk.NORMAL))

    def hook(self, d):
        """Progress hook function to update the GUI status."""
        if d['status'] == 'downloading':
            # Example: '12.3MB of 25.0MB at 1.5MB/s'
            percent_str = d.get('_percent_str', 'N/A')
            self.master.after(0, lambda: self.status_var.set(f"Downloading... {percent_str}"))
        elif d['status'] == 'finished':
            self.master.after(0, lambda: self.status_var.set("Post-processing (Conversion/Merging)..."))


# --- Run the Application ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MediaDownloaderApp(root)
    root.mainloop()