import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import os
import platform
import subprocess
import threading
from pathlib import Path
import sys
from PIL import Image, ImageTk


# --- Path Helper for PyInstaller ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    # During runtime, PyInstaller sets the _MEIPASS attribute
    # to the path of the temporary folder where bundled files are extracted.
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# --- Custom Logger for Error Reporting ---
class YtdlpLogger:
    """A custom logger to capture yt-dlp errors and warnings for the GUI."""

    def __init__(self):
        self.failed_downloads = []

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.failed_downloads.append(msg)


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

        master.title("RonsTechHub YouTube Downloader")

        master.geometry("600x600")
        self.master.grid_columnconfigure(0, weight=1)

        self.default_download_dir = get_download_folder()
        self.audio_quality_options = ["320k (Best)", "192k (Standard)", "128k (Good)"]
        self.video_quality_options = ["2160p (4K)", "1440p (2K)", "1080p (FHD)", "720p (HD)", "480p (SD)"]

        self.download_mode_var = tk.StringVar(value="audio")
        self.input_mode_var = tk.StringVar(value="single")
        self.quality_var = tk.StringVar(value=self.audio_quality_options[0])
        self.status_var = tk.StringVar(value="Ready")
        self.output_dir_var = tk.StringVar(value=str(self.default_download_dir))

        self.url_entries = []
        self.logger = YtdlpLogger()

        self.load_logo()
        self.create_widgets()

    def load_logo(self):
        """Loads and resizes the logo image for the application."""
        logo_filename = "RTH Logo.png"

        try:
            image_path = resource_path(logo_filename)
            logo_img = Image.open(image_path)

            self.icon_img = ImageTk.PhotoImage(logo_img)

            logo_img = logo_img.resize((40, 40), Image.LANCZOS)
            self.tk_logo = ImageTk.PhotoImage(logo_img)

            self.master.iconphoto(False, self.icon_img)

        except Exception as e:
            print(f"Error loading logo: {e}")
            self.tk_logo = None
            self.icon_img = None

    def create_widgets(self):
        # --- APP TITLE AND LOGO ---
        title_frame = ttk.Frame(self.master)
        title_frame.grid(row=0, column=0, pady=(15, 10), sticky='n')

        if self.tk_logo:
            logo_label = ttk.Label(title_frame, image=self.tk_logo)
            logo_label.grid(row=0, column=0, padx=10, sticky='w')

        ttk.Label(title_frame, text="RonsTechHub YouTube Downloader", font=('Arial', 16, 'bold')).grid(row=0, column=1,
                                                                                                       sticky='w')

        # --- WIDGET CONTAINER FRAME ---
        main_controls_frame = ttk.Frame(self.master)
        main_controls_frame.grid(row=1, column=0, padx=10, sticky='new')
        main_controls_frame.grid_columnconfigure(0, weight=1)

        current_row = 0

        # --- 1. DOWNLOAD TYPE (Audio/Video) ---
        type_frame = ttk.LabelFrame(main_controls_frame, text="Download Type")
        type_frame.grid(row=current_row, column=0, pady=10, padx=10, sticky='ew')
        current_row += 1

        ttk.Radiobutton(type_frame, text="Audio (MP3)", variable=self.download_mode_var, value="audio",
                        command=self.update_quality_options).grid(row=0, column=0, padx=10, pady=5)
        ttk.Radiobutton(type_frame, text="Video (MP4)", variable=self.download_mode_var, value="video",
                        command=self.update_quality_options).grid(row=0, column=1, padx=10, pady=5)

        # --- 2. INPUT MODE (Single/Playlist) ---
        input_frame = ttk.LabelFrame(main_controls_frame, text="Input Mode")
        input_frame.grid(row=current_row, column=0, pady=5, padx=10, sticky='ew')
        current_row += 1

        ttk.Radiobutton(input_frame, text="Single Song(s) / Batch URL", variable=self.input_mode_var, value="single",
                        command=self.update_input_fields).grid(row=0, column=0, padx=10, pady=5)
        ttk.Radiobutton(input_frame, text="Entire Playlist/Channel", variable=self.input_mode_var, value="playlist",
                        command=self.update_input_fields).grid(row=0, column=1, padx=10, pady=5)

        # --- 3. INPUT FIELDS (Dynamic URL Section) ---
        self.input_container = ttk.Frame(main_controls_frame)
        self.input_container.grid(row=current_row, column=0, pady=5, padx=10, sticky='ew')
        self.input_container.grid_columnconfigure(0, weight=1)
        current_row += 1
        self.update_input_fields()

        # --- 4. QUALITY SELECTION ---
        quality_frame = ttk.Frame(main_controls_frame)
        quality_frame.grid(row=current_row, column=0, pady=10, padx=10, sticky='w')
        current_row += 1

        ttk.Label(quality_frame, text="Quality:").grid(row=0, column=0, padx=5, sticky='w')
        self.quality_menu = ttk.OptionMenu(quality_frame, self.quality_var, self.quality_var.get(),
                                           *self.audio_quality_options)
        self.quality_menu.grid(row=0, column=1, padx=5)

        # --- 5. OUTPUT FOLDER SELECTION ---
        output_frame = ttk.LabelFrame(main_controls_frame, text="Output Directory")
        output_frame.grid(row=current_row, column=0, pady=10, padx=10, sticky='ew')
        current_row += 1

        output_frame.grid_columnconfigure(0, weight=1)

        ttk.Entry(output_frame, textvariable=self.output_dir_var).grid(row=0, column=0, padx=(5, 0), pady=5,
                                                                       sticky='ew')
        ttk.Button(output_frame, text="Browse", command=self.browse_output_folder).grid(row=0, column=1, padx=5, pady=5)

        # --- 6. ACTION & STATUS ---
        self.download_button = ttk.Button(self.master, text="Start Download", command=self.start_download_thread)
        self.download_button.grid(row=current_row, column=0, pady=15)
        current_row += 1

        ttk.Label(self.master, textvariable=self.status_var, font=('Arial', 10, 'bold'), wraplength=580,
                  justify=tk.LEFT).grid(row=current_row, column=0, pady=5, padx=10, sticky='ew')
        current_row += 1
        ttk.Label(self.master, text=f"Default Folder: {self.default_download_dir.name}").grid(row=current_row, column=0,
                                                                                              pady=(0, 10))

    # --- GUI Update Methods (Unchanged) ---

    def browse_output_folder(self):
        """Opens a dialog to select the output directory."""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)

    def update_quality_options(self):
        """Updates the dropdown menu based on the selected download mode (audio/video)."""
        mode = self.download_mode_var.get()
        options = self.video_quality_options if mode == "video" else self.audio_quality_options

        self.quality_var.set(options[0])
        menu = self.quality_menu["menu"]
        menu.delete(0, "end")
        for item in options:
            menu.add_command(label=item, command=tk._setit(self.quality_var, item))

    def update_input_fields(self):
        """Rebuilds the URL input section based on the selected input mode."""
        for widget in self.input_container.winfo_children():
            widget.destroy()
        self.url_entries = []

        if self.input_mode_var.get() == "single":
            self.add_url_entry()
            ttk.Label(self.input_container, text="Paste URLs one by one:").grid(row=0, column=0, sticky='w',
                                                                                pady=(5, 0), padx=5)
        else:  # playlist mode
            var = tk.StringVar()
            entry = ttk.Entry(self.input_container, textvariable=var)
            entry.grid(row=1, column=0, pady=5, padx=5, sticky='ew')
            self.url_entries.append(var)
            ttk.Label(self.input_container, text="Paste single Playlist/Channel URL:").grid(row=0, column=0, sticky='w',
                                                                                            pady=(5, 0), padx=5)

    def add_url_entry(self, *args):
        """Dynamically adds a new URL input box when the last one is edited."""

        current_rows = len(self.input_container.winfo_children())

        last_entry_var = self.url_entries[-1] if self.url_entries else None

        if last_entry_var and last_entry_var.get().strip() == "":
            return

        var = tk.StringVar()
        entry = ttk.Entry(self.input_container, textvariable=var)

        entry.grid(row=current_rows, column=0, pady=5, padx=5, sticky='ew')

        entry.bind('<KeyRelease>', self.add_url_entry)
        self.url_entries.append(var)
        self.master.update_idletasks()

    # --- Downloader Execution Methods (The Fix is Here) ---

    def start_download_thread(self):
        """Collects all URLs and starts the download process in a separate thread."""

        urls = [v.get().strip() for v in self.url_entries]
        urls = [url for url in urls if url]

        output_dir = self.output_dir_var.get()
        if not output_dir or not Path(output_dir).is_dir():
            messagebox.showerror("Error", "Please select a valid output directory.")
            return

        if not urls:
            messagebox.showerror("Error", "Please enter at least one URL.")
            return

        self.logger = YtdlpLogger()

        self.download_button.config(state=tk.DISABLED)
        self.status_var.set(f"Starting download of {len(urls)} item(s)...")

        download_thread = threading.Thread(target=self.download_media, args=(urls, output_dir))
        download_thread.start()

    def download_media(self, urls, output_dir):
        """Core download logic using yt-dlp."""
        mode = self.download_mode_var.get()
        is_playlist = self.input_mode_var.get() == "playlist"
        selected_quality = self.quality_var.get().split(' ')[0]

        # --- FIX: Explicitly check for and reference bundled FFmpeg ---
        ffmpeg_path = resource_path("ffmpeg.exe")
        ffprobe_path = resource_path("ffprobe.exe")

        ffmpeg_found = False
        try:
            # First, check if the bundled version exists
            if Path(ffmpeg_path).exists() and Path(ffprobe_path).exists():
                # If they exist, we assume the bundling was successful.
                # We skip the system PATH check, as we will use the explicit path below.
                ffmpeg_found = True
            else:
                # If the bundled version is not found, check system PATH as a fallback
                # (useful when running the script directly, not as an EXE)
                subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                ffmpeg_found = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If neither the bundled version nor the system PATH version is found
            self.master.after(0, lambda: messagebox.showerror("Error",
                                                              "FFmpeg is required but not found. Please ensure FFmpeg is in your system's PATH, or that the --add-binary commands for PyInstaller were correct."))
            self.master.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.status_var.set("Error: FFmpeg not found")
            return

        # --- yt-dlp Options Configuration ---
        ydl_opts = {
            'outtmpl': str(Path(output_dir) / '%(title)s.%(ext)s'),
            'keep_intermediate_files': False,
            'ignoreerrors': True,
            'progress_hooks': [self.hook],
            'logger': self.logger,
            'noplaylist': not is_playlist,
        }

        # --- CRITICAL FIX: Only set executables if the bundled files exist ---
        if Path(ffmpeg_path).exists() and Path(ffprobe_path).exists():
            ydl_opts['executables'] = {
                'postprocessor': ffmpeg_path,
                'downloader': ffmpeg_path,
            }

        if mode == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': selected_quality,
                }],
            })

        else:  # Video mode
            target_res = int(selected_quality.replace('p', ''))

            ydl_opts.update({
                'format': f'bestvideo[height<={target_res}]+bestaudio/best',
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)

            if self.logger.failed_downloads:
                num_failed = len(self.logger.failed_downloads)
                total_items = len(urls)

                error_details = "\n\nFailed Items Summary:\n" + "\n".join(self.logger.failed_downloads[:5])
                if num_failed > 5:
                    error_details += f"\n... and {num_failed - 5} more errors."

                self.master.after(0, lambda: self.status_var.set(
                    f"Download Finished! {total_items - num_failed}/{total_items} succeeded."))
                self.master.after(0, lambda: messagebox.showwarning("Download Complete with Errors",
                                                                    f"Successfully downloaded {total_items - num_failed} items.\n{num_failed} items failed to download or process." + error_details))
            else:
                self.master.after(0,
                                  lambda: self.status_var.set(f"Download Complete! Saved to {Path(output_dir).name}"))
                self.master.after(0, lambda: messagebox.showinfo("Success",
                                                                 f"All media downloaded successfully to: {output_dir}"))

        except Exception as e:
            self.master.after(0, lambda: self.status_var.set(f"Critical Error: {e}"))
            self.master.after(0, lambda: messagebox.showerror("Critical Error", f"A critical error occurred: {e}"))

        finally:
            self.master.after(0, lambda: self.download_button.config(state=tk.NORMAL))

    def hook(self, d):
        """Progress hook function to update the GUI status with title, speed, and ETA."""
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', 'N/A')
            speed_str = d.get('_speed_str', 'N/A')
            eta_str = d.get('_eta_str', 'N/A')

            title = d.get('info_dict', {}).get('title', 'Current Item')

            status_text = f"Downloading: '{title}' - {percent_str} at {speed_str} (ETA: {eta_str})"
            self.master.after(0, lambda: self.status_var.set(status_text))

        elif d['status'] == 'finished':
            title = d.get('info_dict', {}).get('title', 'Current Item')
            self.master.after(0, lambda: self.status_var.set(f"Post-processing: '{title}' (Conversion/Merging)..."))

        elif d['status'] == 'error':
            self.master.after(0, lambda: self.status_var.set(f"Download Error: {d['error']}"))


# --- Run the Application ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MediaDownloaderApp(root)
    root.mainloop()