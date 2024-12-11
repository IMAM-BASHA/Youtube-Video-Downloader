import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class VideoDownloader:
    def __init__(self, master):
        self.master = master
        master.title("Enhanced Video Downloader")
        master.geometry("800x600")

        self.url_var = tk.StringVar()
        self.download_path = tk.StringVar()
        self.quality_var = tk.StringVar(value='360p')
        self.concurrent_downloads = tk.IntVar(value=1)
        self.download_queue = []
        self.active_downloads = []
        self.download_count = 0
        self.total_videos = 0
        self.videos_loaded = 0
        self.start_time = None
        self.paused_time = 0
        self.is_timer_running = False
        self.local_storage_file = "download_queue.json"
        self.overall_speed = 0
        self.preview_info = None

        self.create_widgets()
        self.load_queue_from_storage()

    def create_widgets(self):
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.master)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Top panel
        top_panel = ttk.Frame(main_frame)
        top_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        top_panel.grid_columnconfigure(1, weight=1)

        # URL Entry
        ttk.Label(top_panel, text="Video/Playlist URL:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(top_panel, textvariable=self.url_var, width=50).grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="we")

        # Download Path
        ttk.Label(top_panel, text="Download Path:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(top_panel, textvariable=self.download_path, width=50).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="we")
        ttk.Button(top_panel, text="Browse", command=self.browse).grid(row=1, column=3, padx=5, pady=5)

        # Quality Options
        ttk.Label(top_panel, text="Quality:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        quality_frame = ttk.Frame(top_panel)
        quality_frame.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="w")
        qualities = ['360p', '480p', '720p', '1080p', '1440p']
        for i, quality in enumerate(qualities):
            ttk.Radiobutton(quality_frame, text=quality, variable=self.quality_var, value=quality).grid(row=0, column=i, padx=5)

        # Preview Download Button
        preview_button = tk.Button(top_panel, text="Preview Download", command=self.preview_download, bg="lightblue")
        preview_button.grid(row=3, column=0, padx=5, pady=5)

        # Concurrent Downloads
        ttk.Label(top_panel, text="Concurrent Downloads:").grid(row=3, column=1, padx=5, pady=5, sticky="e")
        concurrent_combobox = ttk.Combobox(top_panel, textvariable=self.concurrent_downloads, values=list(range(1, 11)), width=5)
        concurrent_combobox.grid(row=3, column=2, padx=5, pady=5)
        concurrent_combobox.set(1)

        # Download Button
        download_button = tk.Button(top_panel, text="Start Download", command=self.start_download, bg="yellow")
        download_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Overall Progress
        self.overall_progress_frame = ttk.Frame(top_panel)
        self.overall_progress_frame.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky="we")
        self.overall_progress_bar = ttk.Progressbar(self.overall_progress_frame, length=300, mode='determinate')
        self.overall_progress_bar.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        self.overall_time_label = ttk.Label(self.overall_progress_frame, text="Time: 00:00:00")
        self.overall_time_label.pack(side=tk.LEFT, padx=5)
        self.overall_count_button = tk.Button(self.overall_progress_frame, text="0 / 0", state=tk.DISABLED)
        self.overall_count_button.pack(side=tk.LEFT, padx=5)
        self.overall_percentage_label = ttk.Label(self.overall_progress_frame, text="0%")
        self.overall_percentage_label.pack(side=tk.LEFT, padx=5)
        self.overall_speed_label = ttk.Label(self.overall_progress_frame, text="0 MB/s")
        self.overall_speed_label.pack(side=tk.LEFT, padx=5)

        

        # Terminal Output
        self.terminal_frame = ttk.Frame(top_panel)
        self.terminal_frame.grid(row=7, column=0, columnspan=4, padx=5, pady=5, sticky="we")
        self.terminal_text = tk.Text(self.terminal_frame, height=5, width=70, state=tk.DISABLED)
        self.terminal_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        terminal_scrollbar = ttk.Scrollbar(self.terminal_frame, orient="vertical", command=self.terminal_text.yview)
        terminal_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_text.configure(yscrollcommand=terminal_scrollbar.set)

        # Bottom panel with border
        bottom_panel = ttk.Frame(main_frame, style='Border.TFrame')
        bottom_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        bottom_panel.grid_columnconfigure(0, weight=1)
        bottom_panel.grid_rowconfigure(0, weight=1)

        # Download Queue
        self.queue_frame = ttk.Frame(bottom_panel)
        self.queue_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.queue_frame.grid_columnconfigure(0, weight=1)
        self.queue_frame.grid_rowconfigure(0, weight=1)

        self.queue_canvas = tk.Canvas(self.queue_frame)
        self.queue_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.queue_frame, orient="vertical", command=self.queue_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.queue_canvas.configure(yscrollcommand=scrollbar.set)

        self.inner_frame = ttk.Frame(self.queue_canvas)
        self.queue_canvas_window = self.queue_canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self.on_frame_configure)
        self.queue_canvas.bind("<Configure>", self.on_canvas_configure)

        # Enable two-finger scrolling
        self.queue_canvas.bind('<Enter>', self._bind_mousewheel)
        self.queue_canvas.bind('<Leave>', self._unbind_mousewheel)

        # Add border style
        style = ttk.Style()
        style.configure('Border.TFrame', borderwidth=3, relief='solid')

    def on_frame_configure(self, event):
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        width = event.width
        self.queue_canvas.itemconfig(self.queue_canvas_window, width=width)

    def _bind_mousewheel(self, event):
        self.queue_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.queue_canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        if self.queue_canvas.winfo_height() < self.inner_frame.winfo_reqheight():
            self.queue_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def browse(self):
        download_dir = filedialog.askdirectory()
        if download_dir:
            self.download_path.set(download_dir)
            self.log_to_terminal(f"Download path set to: {download_dir}")

    def preview_download(self):
        url = self.url_var.get()
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL.")
            return

        self.log_to_terminal(f"Analyzing URL: {url}")
        threading.Thread(target=self.analyze_url, args=(url,), daemon=True).start()

    def analyze_url(self, url):
        ydl_opts = {
            'format': 'best',
            'noplaylist': False,
            'logger': YoutubeDLLogger(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    # It's a playlist
                    self.preview_info = {
                        'type': 'playlist',
                        'title': info.get('title', 'Untitled Playlist'),
                        'entries': [
                            {
                                'title': entry.get('title', 'Untitled Video'),
                                'formats': entry.get('formats', []),
                                'duration': entry.get('duration', 0)
                                
                            }
                            for entry in info['entries']
                        ]
                    }
                else:
                    # It's a single video
                    self.preview_info = {
                        'type': 'video',
                        'title': info.get('title', 'Untitled Video'),
                        'formats': info.get('formats', []),
                        'duration': info.get('duration', 0)
                    }
                self.master.after(0, self.update_preview)
            except Exception as e:
                self.log_to_terminal(f"An error occurred during preview: {str(e)}")
                self.master.after(0, lambda: messagebox.showerror("Error", f"An error occurred during preview: {str(e)}"))


    def update_preview(self):
        if self.preview_info:
            if self.preview_info['type'] == 'playlist':
                message = f"Playlist: {self.preview_info['title']}\n"
                message += f"Number of videos: {len(self.preview_info['entries'])}\n\n"
                total_duration = sum(entry['duration'] for entry in self.preview_info['entries'])
                message += f"Total duration: {self.format_duration(total_duration)}\n\n"
                for i, entry in enumerate(self.preview_info['entries'][:5], 1):
                    message += f"Video {i}: {entry['title']}\n"
                    message += f"  Duration: {self.format_duration(entry['duration'])}\n"
                    for fmt in entry['formats']:
                        if fmt.get('height') == int(self.quality_var.get()[:-1]):
                            if fmt.get('filesize'):
                                size_mb = fmt['filesize'] / (1024 * 1024)
                                message += f"  Quality: {fmt['height']}p - Size: {size_mb:.2f} MB\n"
                            break
                    else:
                        message += f"  Quality: {self.quality_var.get()} not available\n"
                if len(self.preview_info['entries']) > 5:
                    message += "...\n"
            else:
                message = f"Video: {self.preview_info['title']}\n"
                message += f"Duration: {self.format_duration(self.preview_info['duration'])}\n"
                for fmt in self.preview_info['formats']:
                    if fmt.get('height') == int(self.quality_var.get()[:-1]):
                        if fmt.get('filesize'):
                            size_mb = fmt['filesize'] / (1024 * 1024)
                            message += f"Quality: {fmt['height']}p - Size: {size_mb:.2f} MB\n"
                        break
                else:
                    message += f"Quality: {self.quality_var.get()} not available\n"
            self.log_to_terminal(message)

    def start_download(self):
        if not self.download_path.get():
            messagebox.showerror("Error", "Please select a download path first.")
            self.browse()
            return
    
        if not os.path.isdir(self.download_path.get()):
            messagebox.showerror("Error", "The selected download path is not a valid directory.")
            self.browse()
            return
    
        self.log_to_terminal("Starting download process...")
        if not self.is_timer_running:
            self.start_timer()
        threading.Thread(target=self.process_url, args=(self.url_var.get(),), daemon=True).start()

    def process_url(self, url):
        quality = self.quality_var.get()
        ydl_opts = {
            'format': f'bestvideo[height<={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality[:-1]}][ext=mp4]/best',
            'outtmpl': os.path.join(self.download_path.get(), '%(title)s.%(ext)s'),
            'subtitleslangs': ['en'],
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'srt',
            'logger': YoutubeDLLogger(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:  # It's a playlist
                    self.total_videos = len(info['entries'])
                    self.videos_loaded = 0
                    self.log_to_terminal(f"Playlist detected with {self.total_videos} videos.")
                    for entry in info['entries']:
                        self.videos_loaded += 1
                        self.log_to_terminal(f"Processing video {self.videos_loaded}/{self.total_videos}: {entry['title']}")
                        self.add_to_queue(entry)
                else:  # It's a single video
                    self.total_videos = 1
                    self.videos_loaded = 1
                    self.log_to_terminal("Single video detected.")
                    self.add_to_queue(info)
                self.process_queue()
            except Exception as e:
                self.log_to_terminal(f"An error occurred: {str(e)}")
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def add_to_queue(self, video_info):
        frame = ttk.Frame(self.inner_frame)
        frame.pack(fill=tk.X, padx=5, pady=5)

        sequence_number = len(self.download_queue) + len(self.active_downloads) + 1
        title_label = ttk.Label(frame, text=f"{sequence_number}. {video_info['title']} ({self.quality_var.get()})")
        title_label.pack(side=tk.TOP, fill=tk.X)

        progress_bar = ttk.Progressbar(frame, length=300, mode='determinate')
        progress_bar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        info_frame = ttk.Frame(frame)
        info_frame.pack(side=tk.TOP, fill=tk.X)

        speed_label = ttk.Label(info_frame, text="")
        speed_label.pack(side=tk.LEFT, padx=5)

        percentage_label = ttk.Label(info_frame, text="0%")
        percentage_label.pack(side=tk.LEFT, padx=5)

        time_label = ttk.Label(info_frame, text="Time: 00:00:00")
        time_label.pack(side=tk.LEFT, padx=5)

        storage_label = ttk.Label(info_frame, text="Storage: 0 MB")
        storage_label.pack(side=tk.LEFT, padx=5)

        button_frame = ttk.Frame(info_frame)
        button_frame.pack(side=tk.RIGHT)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=lambda: self.cancel_download(sequence_number))
        cancel_button.pack(side=tk.LEFT, padx=5)

        download_item = {
            'info': video_info,
            'frame': frame,
            'progress_bar': progress_bar,
            'speed_label': speed_label,
            'percentage_label': percentage_label,
            'time_label': time_label,
            'title_label': title_label,
            'storage_label': storage_label,
            'cancel_button': cancel_button,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'ydl': None,
            'thread': None,
            'stop_event': threading.Event(),
            'sequence_number': sequence_number,
            'start_time': None,
            'paused_time': 0
        }
        self.download_queue.append(download_item)
        ttk.Separator(self.inner_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)
        self.save_queue_to_storage()
        return download_item
    def format_duration(self, duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"

    def process_queue(self):
        max_concurrent = self.concurrent_downloads.get()
        while len(self.active_downloads) < max_concurrent and self.download_queue:
            download_item = self.download_queue.pop(0)
            self.start_download_item(download_item)


    def start_download_item(self, download_item):
        self.active_downloads.append(download_item)
        download_item['start_time'] = time.time()
        download_item['thread'] = threading.Thread(target=self.download_video, args=(download_item,), daemon=True)
        download_item['thread'].start()

    def download_video(self, download_item):
        if download_item not in self.active_downloads:
            self.log_to_terminal(f"Warning: Attempted to download an item not in active downloads: {download_item['info']['title']}")
            return

        video_info = download_item['info']
        progress_bar = download_item['progress_bar']
        speed_label = download_item['speed_label']
        percentage_label = download_item['percentage_label']
        time_label = download_item['time_label']
        storage_label = download_item['storage_label']

        quality = int(self.quality_var.get()[:-1])
        ydl_opts = {
            'format': f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': os.path.join(self.download_path.get(), f'{download_item["sequence_number"]}.%(title)s ({self.quality_var.get()}).%(ext)s'),
            'subtitleslangs': ['en'],
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'srt',
            'progress_hooks': [lambda d: self.update_progress(d, download_item)],
            'logger': YoutubeDLLogger(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            download_item['ydl'] = ydl
            try:
                self.log_to_terminal(f"Starting download of: {video_info['title']}")
                ydl.download([video_info['webpage_url']])
            except yt_dlp.utils.DownloadError as e:
                if "This video is available to this channel's members" in str(e):
                    self.log_to_terminal(f"Skipping video '{video_info['title']}': Members-only content")
                else:
                    self.log_to_terminal(f"An error occurred while downloading {video_info['title']}: {str(e)}")
            finally:
                download_item['ydl'] = None

        end_time = time.time()
        duration = end_time - download_item['start_time']
        hours, rem = divmod(duration, 3600)
        minutes, seconds = divmod(rem, 60)

        success_message = f"Download of '{video_info['title']}' completed in {int(hours)}h {int(minutes)}m {int(seconds)}s"
        self.log_to_terminal(success_message)

        self.master.after(0, lambda: self.remove_download_item(download_item))
        self.download_count += 1
        self.update_overall_progress()
        self.master.after(0, self.process_queue)
        # self.save_queue_to_storage()

    def remove_download_item(self, download_item):
        if download_item in self.active_downloads:
            self.active_downloads.remove(download_item)
        elif download_item in self.download_queue:
            self.download_queue.remove(download_item)
        self.master.after(0, download_item['frame'].destroy)
        self.save_queue_to_storage()

    def update_progress(self, d, download_item):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = d['downloaded_bytes'] / total_bytes * 100
                self.master.after(0, lambda p=percent: download_item['progress_bar'].config(value=p))
                self.master.after(0, lambda p=percent: download_item['percentage_label'].config(text=f"{p:.2f}%"))
                download_item['downloaded_bytes'] = d['downloaded_bytes']
                download_item['total_bytes'] = total_bytes

                downloaded_mb = d['downloaded_bytes'] / (1024 * 1024)
                total_mb = total_bytes / (1024 * 1024)
                storage_str = f"Storage: {downloaded_mb:.2f} MB / {total_mb:.2f} MB"
                self.master.after(0, lambda s=storage_str: download_item['storage_label'].config(text=s))

            speed = d.get('speed', 0)
            if speed:
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
                self.master.after(0, lambda s=speed_str: download_item['speed_label'].config(text=s))
                self.overall_speed = speed
                self.master.after(0, lambda s=speed_str: self.overall_speed_label.config(text=s))

            elapsed_time = time.time() - (download_item['start_time'] or time.time())
            hours, rem = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(rem, 60)
            time_str = f"Time: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            self.master.after(0, lambda t=time_str: download_item['time_label'].config(text=t))

        self.update_overall_progress()

    def cancel_download(self, sequence_number):
        download_item = self.get_download_item(sequence_number)
        if download_item:
            if messagebox.askyesno("Cancel Download", f"Are you sure you want to cancel the download of '{download_item['info']['title']}'?"):
                self.log_to_terminal(f"Cancelled download of: {download_item['info']['title']}")
                download_item['stop_event'].set()
                if download_item['ydl']:
                    download_item['ydl'].params['playlist_items'] = ''
                if download_item['thread']:
                    download_item['thread'].join(timeout=1)
                self.remove_download_item(download_item)
                self.process_queue()
        self.save_queue_to_storage()

    def get_download_item(self, sequence_number):
        all_items = self.active_downloads + self.download_queue
        for item in all_items:
            if item['sequence_number'] == sequence_number:
                return item
        return None

   

    def pause_all_downloads(self):
        for download_item in self.active_downloads:
            if download_item['ydl']:
                download_item['ydl'].params['playlist_items'] = ''
            download_item['paused_time'] = time.time() - download_item['start_time']
        self.download_queue = self.active_downloads + self.download_queue
        self.active_downloads = []
        self.save_queue_to_storage()
        
    def update_overall_progress(self):
        if self.total_videos > 0:
            progress = (self.download_count / self.total_videos) * 100
            self.overall_progress_bar['value'] = progress
            self.overall_percentage_label['text'] = f"{progress:.2f}%"
            self.overall_count_button['text'] = f"{self.download_count} / {self.total_videos}"
            
            if self.download_count == self.total_videos:
                self.show_completion_message()
                self.stop_timer()
                self.reset_ui()

    

    def start_timer(self):
        if not self.is_timer_running:
            self.is_timer_running = True
            self.start_time = time.time()
            self.update_timer()

    def stop_timer(self):
        if self.is_timer_running:
            self.is_timer_running = False
            self.paused_time += time.time() - self.start_time

    def update_timer(self):
        if self.is_timer_running:
            elapsed_time = time.time() - self.start_time + self.paused_time
            hours, rem = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(rem, 60)
            self.overall_time_label['text'] = f"Time: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            self.master.after(1000, self.update_timer)

    def show_completion_message(self):
        if not self.active_downloads and not self.download_queue:
            messagebox.showinfo("Download Complete", "All videos in the queue have been successfully downloaded.")

    def reset_ui(self):
        self.overall_progress_bar['value'] = 0
        self.overall_count_button['text'] = "0 / 0"
        self.overall_percentage_label['text'] = "0%"
        self.overall_speed_label['text'] = "0 MB/s"
        self.overall_time_label['text'] = "Time: 00:00:00"
        self.paused_time = 0
        self.start_time = None
        self.download_count = 0
        self.total_videos = 0
        self.is_timer_running = False
        self.save_queue_to_storage()
        
    def log_to_terminal(self, message):
        self.terminal_text.configure(state=tk.NORMAL)
        self.terminal_text.insert(tk.END, message + "\n")
        self.terminal_text.see(tk.END)
        self.terminal_text.configure(state=tk.DISABLED)

    def save_queue_to_storage(self):
        queue_data = []
        for item in self.download_queue + self.active_downloads:
            queue_data.append({
                'url': item['info']['webpage_url'],
                'title': item['info']['title'],
                'downloaded_bytes': item['downloaded_bytes'],
                'total_bytes': item['total_bytes'],
                'sequence_number': item['sequence_number'],
                'quality': self.quality_var.get(),
                'download_path': self.download_path.get()
            })
        data_to_save = {
            'queue': queue_data,
            'download_count': self.download_count,
            'total_videos': self.total_videos,
            'paused_time': self.paused_time + (time.time() - self.start_time if self.start_time else 0)
        }
        with open(self.local_storage_file, 'w') as f:
            json.dump(queue_data, f)

    def load_queue_from_storage(self):
        if os.path.exists(self.local_storage_file):
            with open(self.local_storage_file, 'r') as f:
                data = json.load(f)
        
            if isinstance(data, list):
            # Old format
                queue_data = data
                self.download_count = 0
                self.total_videos = len(queue_data)
                self.paused_time = 0
            elif isinstance(data, dict):
            # New format
                queue_data = data.get('queue', [])
                self.download_count = data.get('download_count', 0)
                self.total_videos = data.get('total_videos', len(queue_data))
                self.paused_time = data.get('paused_time', 0)
            else:
                self.log_to_terminal("Error: Invalid data format in storage file")
                return

            for item in queue_data:
                self.add_to_queue_from_storage(item)
        
            self.update_overall_progress()
            if self.total_videos > 0:
                self.start_timer()
                self.process_queue()
                

    def add_to_queue_from_storage(self, item):
        video_info = {
            'webpage_url': item['url'],
            'title': item['title']
        }
        download_item = self.add_to_queue(video_info)
        download_item['downloaded_bytes'] = item['downloaded_bytes']
        download_item['total_bytes'] = item['total_bytes']
        download_item['sequence_number'] = item.get('sequence_number', len(self.download_queue))
        self.download_path.set(item.get('download_path', self.download_path.get()))
        self.quality_var.set(item.get('quality', self.quality_var.get()))
        self.update_progress({'status': 'downloading', 'downloaded_bytes': item['downloaded_bytes'], 'total_bytes': item['total_bytes']}, download_item)

    def on_closing(self):
        self.save_queue_to_storage()
        incomplete_downloads = len(self.download_queue) + len(self.active_downloads)
        if incomplete_downloads > 0:
            if messagebox.askyesno("Quit", f"There are {incomplete_downloads} incomplete downloads. Are you sure you want to quit?"):
                self.master.destroy()
        else:
            self.master.destroy()

class YoutubeDLLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/download_queue':
            queue_data = json.dumps({'queue': list(range(len(app.download_queue)))})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(queue_data.encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    httpd = HTTPServer(('localhost', 8000), RequestHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    root.mainloop()