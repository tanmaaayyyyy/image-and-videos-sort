import os
import shutil
import datetime
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

# Supported extensions
image_exts = ('.jpg', '.jpeg', '.png', '.webp')
video_exts = ('.mp4', '.mov', '.avi', '.mkv', '.3gp')

class SorterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Sorter")
        self.geometry("600x400")

        self.folder_path = tk.StringVar()
        self.action = tk.StringVar(value='copy')

        # Folder selection
        tk.Label(self, text="Select folder to sort:").pack(pady=5)
        folder_frame = tk.Frame(self)
        folder_frame.pack(fill='x', padx=10)
        tk.Entry(folder_frame, textvariable=self.folder_path).pack(side='left', fill='x', expand=True)
        tk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side='right')

        # Move or Copy option
        tk.Label(self, text="Choose action:").pack(pady=5)
        action_frame = tk.Frame(self)
        action_frame.pack()
        tk.Radiobutton(action_frame, text="Copy", variable=self.action, value='copy').pack(side='left', padx=10)
        tk.Radiobutton(action_frame, text="Move", variable=self.action, value='move').pack(side='left', padx=10)

        # Start button
        tk.Button(self, text="Start Sorting", command=self.start_sorting).pack(pady=10)

        # Status box
        tk.Label(self, text="Status:").pack()
        self.status_box = scrolledtext.ScrolledText(self, height=10, state='disabled')
        self.status_box.pack(fill='both', padx=10, pady=5, expand=True)

    def log(self, message):
        self.status_box.configure(state='normal')
        self.status_box.insert(tk.END, message + '\n')
        self.status_box.see(tk.END)
        self.status_box.configure(state='disabled')

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def start_sorting(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder.")
            return
        self.status_box.configure(state='normal')
        self.status_box.delete(1.0, tk.END)
        self.status_box.configure(state='disabled')

        # Run sorting in a thread so GUI stays responsive
        threading.Thread(target=self.sort_files, args=(folder, self.action.get()), daemon=True).start()

    def get_image_date(self, path):
        try:
            img = Image.open(path)
            exif = img._getexif()
            if not exif:
                return None
            for tag, value in exif.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "DateTimeOriginal":
                    return datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        except:
            return None

    def get_video_date(self, path):
        try:
            parser = createParser(path)
            if not parser:
                return None
            metadata = extractMetadata(parser)
            if metadata and metadata.has("creation_date"):
                return metadata.get("creation_date")
        except:
            return None

    def get_modified_date(self, path):
        timestamp = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(timestamp)

    def sort_file(self, file_path, output_dir, action):
        ext = os.path.splitext(file_path)[1].lower()
        date = None

        try:
            if ext in image_exts:
                date = self.get_image_date(file_path)
            elif ext in video_exts:
                date = self.get_video_date(file_path)

            if not date:
                date = self.get_modified_date(file_path)

            folder_name = date.strftime("%Y-%m")
            dest_folder = os.path.join(output_dir, folder_name)
        except:
            dest_folder = os.path.join(output_dir, "undated_or_error")

        os.makedirs(dest_folder, exist_ok=True)
        dest_path = os.path.join(dest_folder, os.path.basename(file_path))

        try:
            if action == 'move':
                shutil.move(file_path, dest_path)
                self.log(f"Moved: {file_path} → {dest_folder}")
            else:
                shutil.copy2(file_path, dest_path)
                self.log(f"Copied: {file_path} → {dest_folder}")
        except Exception as e:
            self.log(f"Error processing {file_path}: {e}")
            # Attempt to copy to undated folder
            undated_folder = os.path.join(output_dir, "undated_or_error")
            os.makedirs(undated_folder, exist_ok=True)
            shutil.copy2(file_path, undated_folder)
            self.log(f"Copied to undated_or_error: {file_path}")

    def sort_files(self, folder, action):
        output_dir = os.path.join(folder, "sorted_output")
        undated_dir = os.path.join(output_dir, "undated_or_error")
        os.makedirs(undated_dir, exist_ok=True)

        for root, _, files in os.walk(folder):
            # Prevent sorting files inside sorted_output folder again
            if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
                continue

            for file in files:
                if file.lower().endswith(image_exts + video_exts):
                    file_path = os.path.join(root, file)
                    self.sort_file(file_path, output_dir, action)

        self.log("\n✅ Sorting completed!")

if __name__ == "__main__":
    app = SorterGUI()
    app.mainloop()
