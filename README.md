# Duplicate Image Finder

A small Python desktop application for finding duplicate images in a folder. It checks for exact file matches with SHA-256 and can also find visually similar images with perceptual hashing (pHash).

The app lets you review the results, preview the original and duplicate images, and move unwanted copies to your system Trash.

## Features

- **Folder scanning** — scans the selected folder and its subfolders.
- **Exact duplicate detection** — uses SHA-256 to find files with identical contents, even if their names or extensions are different.
- **Visual duplicate detection** — uses pHash to find many resized or recompressed versions of an image.
- **Adjustable threshold** — choose how closely images must match for pHash detection.
- **Image previews** — compare the retained image with a duplicate candidate before taking action.
- **Safer cleanup** — move selected duplicates, or all listed duplicates, to the system Trash after confirmation.
- **CSV report** — export scan results, file paths, match types, pHash distances, file sizes, and unreadable-file errors.

## Requirements

- Python 3.8 or newer
- Tkinter
- Pillow
- ImageHash
- Send2Trash

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/duplicate-image-finder.git
cd duplicate-image-finder
```

Create and activate a virtual environment:

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**

```powershell
py -m venv .venv
.venv\\Scripts\\activate
```

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the application

```bash
python duplicate_image_finder.py
```

On macOS, you can use `python3` if the `python` command is not available.

## How to use it

1. Open the application.
2. Select the folder you want to scan.
3. Set the pHash threshold. The default value is `6`.
4. Click **Scan** and wait for the scan to finish.
5. Review the duplicate list. Select a row to preview the original and duplicate candidate.
6. Select one or more rows and click **Move Selected to Trash**, or choose **Move ALL Duplicates to Trash**.
7. Confirm the action when prompted.
8. Use **Export CSV Report** if you want to save the scan results.

The app keeps the first image encountered in each detected group and lists later matches as duplicate candidates.

## How duplicate detection works

The application uses two checks:

### SHA-256

Each file is read and its SHA-256 hash is calculated. If two files have the same hash, their file contents are identical. This is reliable for exact duplicates, regardless of filename.

### Perceptual hash (pHash)

The image is opened, orientation is corrected where possible, and a perceptual hash is calculated. The app compares pHash values using Hamming distance.

A smaller distance means the hashes are more alike. This can help identify images that have been resized or recompressed, even when their file contents are no longer identical.

## Choosing a pHash threshold

The threshold is a Hamming distance, **not a percentage**.

- **Lower values** are stricter and return fewer visual matches.
- **Higher values** are more permissive and may return more candidates, including false positives.
- Start with `6`, review the previews, and adjust it based on your image collection.

pHash is not a guarantee that two files are the same photograph. Cropping, rotation, edits, overlays, or very different image versions may affect detection. Different images that look alike can also be flagged when the threshold is high.

## Important notes

- Review the results before moving files to Trash.
- The first encountered image is treated as the original; scan order determines which copy is kept.
- Moving files to Trash depends on operating-system and filesystem support. Some network or mounted locations may not support it.
- Unreadable or unsupported files are skipped and included in the error section of the CSV report.
- Keep a backup of important images before cleaning a large collection.

## Project files

```text
duplicate-image-finder/
├── duplicate_image_finder.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Contributing

Suggestions and improvements are welcome. If you find a problem, please open an issue with steps to reproduce it. Pull requests are also welcome.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
