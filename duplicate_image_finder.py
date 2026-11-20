import csv
import hashlib
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk, ImageOps
import imagehash
from send2trash import send2trash

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".webp", ".tif", ".tiff", ".ico"
}


@dataclass
class ImageRecord:
    path: Path
    sha256: str
    phash: object
    size: int


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_phash(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        return imagehash.phash(image)


def scan_images(folder, threshold, progress_callback=None):
    paths = []
    for root, _, files in os.walk(folder):
        for name in files:
            path = Path(root) / name
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                paths.append(path)

    records = []
    errors = []
    total = len(paths)

    for index, path in enumerate(paths, start=1):
        try:
            record = ImageRecord(
                path=path,
                sha256=sha256_file(path),
                phash=image_phash(path),
                size=path.stat().st_size
            )
            records.append(record)
        except Exception as exc:
            errors.append((str(path), str(exc)))

        if progress_callback:
            progress_callback(index, total, str(path))


    groups = []
    for record in records:
        matched_group = None
        for group in groups:
            representative = group[0]
            if record.sha256 == representative.sha256:
                matched_group = group
                break
            if (record.phash - representative.phash) <= threshold:
                matched_group = group
                break

        if matched_group is None:
            groups.append([record])
        else:
            matched_group.append(record)

    duplicate_rows = []
    for group in groups:
        if len(group) > 1:
            original = group[0]
            for duplicate in group[1:]:
                distance = original.phash - duplicate.phash
                match_type = "Exact (SHA-256)" if original.sha256 == duplicate.sha256 else "Visual (pHash)"
                duplicate_rows.append({
                    "original": original,
                    "duplicate": duplicate,
                    "distance": distance,
                    "match_type": match_type
                })

    return duplicate_rows, errors, total


class DuplicateImageFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate Image Finder")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)

        self.folder_var = tk.StringVar()
        self.threshold_var = tk.IntVar(value=6)
        self.status_var = tk.StringVar(value="Choose a folder to begin.")
        self.results = []
        self.errors = []
        self.preview_refs = []

        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer, text="Duplicate Image Finder",
            font=("TkDefaultFont", 20, "bold")
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text="Find exact and visually similar images, review them, then move duplicates to Trash.",
        ).pack(anchor="w", pady=(2, 12))

        folder_frame = ttk.Frame(outer)
        folder_frame.pack(fill="x", pady=4)
        ttk.Entry(folder_frame, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_frame, text="Choose Folder", command=self.choose_folder).pack(side="left", padx=(8, 0))
        ttk.Button(folder_frame, text="Scan", command=self.start_scan).pack(side="left", padx=(8, 0))

        settings = ttk.Frame(outer)
        settings.pack(fill="x", pady=8)
        ttk.Label(settings, text="pHash threshold:").pack(side="left")
        ttk.Spinbox(
            settings, from_=0, to=20, width=5,
            textvariable=self.threshold_var
        ).pack(side="left", padx=6)
        ttk.Label(
            settings,
            text="Lower = stricter match. 0 means exact pHash match; higher values find more visual variations.",
        ).pack(side="left", padx=8)

        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 2))
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w", pady=(0, 8))

        body = ttk.Panedwindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body, padding=(8, 0, 0, 0))
        body.add(left, weight=3)
        body.add(right, weight=2)

        columns = ("type", "distance", "original", "duplicate")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("type", text="Match type")
        self.tree.heading("distance", text="pHash distance")
        self.tree.heading("original", text="Original (kept)")
        self.tree.heading("duplicate", text="Duplicate (candidate)")
        self.tree.column("type", width=120, stretch=False)
        self.tree.column("distance", width=100, stretch=False)
        self.tree.column("original", width=220)
        self.tree.column("duplicate", width=220)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_preview)

        ttk.Label(right, text="Image preview", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        preview_frame = ttk.Frame(right)
        preview_frame.pack(fill="both", expand=True, pady=6)

        self.original_preview = ttk.Label(preview_frame, text="Select a result")
        self.original_preview.pack(fill="both", expand=True, pady=4)
        self.original_caption = ttk.Label(preview_frame, text="Original")
        self.original_caption.pack(anchor="w")

        ttk.Separator(preview_frame).pack(fill="x", pady=8)

        self.duplicate_preview = ttk.Label(preview_frame, text="")
        self.duplicate_preview.pack(fill="both", expand=True, pady=4)
        self.duplicate_caption = ttk.Label(preview_frame, text="Duplicate")
        self.duplicate_caption.pack(anchor="w")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Move Selected to Trash", command=self.trash_selected).pack(side="left")
        ttk.Button(actions, text="Move ALL Duplicates to Trash", command=self.trash_all).pack(side="left", padx=8)
        ttk.Button(actions, text="Export CSV Report", command=self.export_report).pack(side="left")
        ttk.Button(actions, text="Clear Results", command=self.clear_results).pack(side="right")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Select folder to scan")
        if folder:
            self.folder_var.set(folder)

    def start_scan(self):
        folder = self.folder_var.get().strip()
        if not folder or not Path(folder).is_dir():
            messagebox.showerror("Invalid folder", "Please choose a valid folder.")
            return
        try:
            threshold = self.threshold_var.get()
            if not 0 <= threshold <= 20:
                raise ValueError
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid threshold", "Choose a pHash threshold between 0 and 20.")
            return

        self.clear_results()
        self.progress["value"] = 0
        self.status_var.set("Scanning images...")
        threading.Thread(
            target=self._scan_worker,
            args=(Path(folder), threshold),
            daemon=True
        ).start()

    def _scan_worker(self, folder, threshold):
        def progress(index, total, current):
            self.root.after(0, self._update_progress, index, total, current)

        try:
            results, errors, total = scan_images(folder, threshold, progress)
            self.root.after(0, self._scan_complete, results, errors, total)
        except Exception as exc:
            error_message = str(exc)
            self.root.after(0, lambda message=error_message: messagebox.showerror("Scan failed", message))

    def _update_progress(self, index, total, current):
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = index
        self.status_var.set(f"Scanning {index}/{total}: {current}")

    def _scan_complete(self, results, errors, total):
        self.results = results
        self.errors = errors

        for index, row in enumerate(results):
            self.tree.insert(
                "", "end", iid=str(index),
                values=(
                    row["match_type"],
                    row["distance"],
                    str(row["original"].path),
                    str(row["duplicate"].path)
                )
            )

        self.status_var.set(
            f"Scan complete. Checked {total} image(s); found {len(results)} duplicate(s); "
            f"{len(errors)} file(s) could not be read."
        )
        messagebox.showinfo(
            "Scan complete",
            f"Images scanned: {total}\nDuplicates found: {len(results)}\nUnreadable files: {len(errors)}"
        )

    def show_preview(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        row = self.results[int(selection[0])]
        self._set_preview(self.original_preview, self.original_caption, row["original"].path, "Original (kept)")
        self._set_preview(self.duplicate_preview, self.duplicate_caption, row["duplicate"].path, "Duplicate (candidate)")

    def _set_preview(self, widget, caption, path, label):
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((360, 220))
                photo = ImageTk.PhotoImage(image.copy())
            self.preview_refs.append(photo)
            widget.configure(image=photo, text="")
            caption.configure(text=f"{label}: {path.name}")
        except Exception as exc:
            widget.configure(image="", text=f"Preview unavailable: {exc}")
            caption.configure(text=str(path))

    def _move_rows_to_trash(self, indices):
        if not indices:
            messagebox.showinfo("Nothing selected", "There are no duplicate images to move.")
            return

        prompt = f"Move {len(indices)} duplicate image(s) to your system Trash?"
        if not messagebox.askyesno("Confirm deletion", prompt):
            return

        moved = 0
        failures = []
        for index in sorted(indices, reverse=True):
            row = self.results[index]
            path = row["duplicate"].path
            try:
                if path.exists():
                    send2trash(str(path))
                    moved += 1
            except Exception as exc:
                failures.append(f"{path}: {exc}")

        remaining = []
        for index, row in enumerate(self.results):
            if index not in indices or row["duplicate"].path.exists():
                remaining.append(row)
        self.results = remaining
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, row in enumerate(self.results):
            self.tree.insert(
                "", "end", iid=str(index),
                values=(row["match_type"], row["distance"],
                        str(row["original"].path), str(row["duplicate"].path))
            )

        summary = f"Moved {moved} image(s) to Trash."
        if failures:
            summary += "\n\nSome files could not be moved:\n" + "\n".join(failures[:8])
        messagebox.showinfo("Operation complete", summary)
        self.status_var.set(summary.replace("\n", " "))

    def trash_selected(self):
        selected = self.tree.selection()
        self._move_rows_to_trash([int(item) for item in selected])

    def trash_all(self):
        self._move_rows_to_trash(list(range(len(self.results))))

    def export_report(self):
        if not self.results and not self.errors:
            messagebox.showinfo("No report data", "Run a scan before exporting a report.")
            return

        default_name = f"duplicate_report_{datetime.now():%Y%m%d_%H%M%S}.csv"
        destination = filedialog.asksaveasfilename(
            title="Save duplicate report",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")]
        )
        if not destination:
            return

        try:
            with open(destination, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Match type", "pHash distance", "Original path",
                    "Duplicate path", "Original size (bytes)", "Duplicate size (bytes)"
                ])
                for row in self.results:
                    writer.writerow([
                        row["match_type"], row["distance"],
                        str(row["original"].path), str(row["duplicate"].path),
                        row["original"].size, row["duplicate"].size
                    ])
                if self.errors:
                    writer.writerow([])
                    writer.writerow(["Unreadable files"])
                    writer.writerow(["Path", "Error"])
                    writer.writerows(self.errors)
            messagebox.showinfo("Report saved", f"CSV report saved to:\n{destination}")
        except OSError as exc:
            messagebox.showerror("Could not save report", str(exc))

    def clear_results(self):
        self.results = []
        self.errors = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.original_preview.configure(image="", text="Select a result")
        self.duplicate_preview.configure(image="", text="")
        self.original_caption.configure(text="Original")
        self.duplicate_caption.configure(text="Duplicate")
        self.preview_refs.clear()
        self.status_var.set("Choose a folder to begin.")
        self.progress["value"] = 0


if __name__ == "__main__":
    root = tk.Tk()
    app = DuplicateImageFinder(root)
    root.mainloop()
