# ROI Tool — Camera Archive Edition

A desktop application for drawing, managing, and visualizing **Region of Interest (ROI) polygons** on camera images. Designed for teams that configure vehicle detection, camera analytics, or any system that uses polygon-based zones.

All data is stored **locally** — nothing is lost after closing the app.

---

## Features

- **Draw ROI polygons** by clicking directly on an image
- **Visualize ROI polygons** by pasting coordinates onto an image
- **Camera archive** — organize multiple cameras, each with multiple named ROIs
- **Sidebar navigator** for quick switching between cameras and ROIs
- **Local persistence** — all data saved automatically to `~/.roi_tool/`
- **Multiple coordinate formats** for easy integration with other systems
- **Normalized coordinates** — outputs values between `0.0` and `1.0` relative to image dimensions

---

## Screenshots

| Camera Archive | Draw ROI | Visualize ROI |
|---|---|---|
| Sidebar with camera/ROI tree | Click to place polygon vertices | Paste coordinates to preview overlay |

---

## Running the App

### Option A — Standalone Executable (Recommended, no Python needed)

> Pre-built executables require no installation. Just download and double-click.

**Windows:**
1. Run `build_windows.bat` on any Windows machine that has Python installed
2. Find the built executable at `dist/ROITool.exe`
3. Copy `ROITool.exe` to any Windows PC — no Python or libraries needed

**Linux:**
1. Run `./build_linux.sh` on any Linux machine that has Python installed
2. Find the built binary at `dist/ROITool`
3. Copy `ROITool` to any Linux PC — no Python or libraries needed

---

### Option B — Run from Source

**Requirements:**
- Python 3.9 or newer
- pip

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Run:**

```bash
python3 app.py
```

---

## How to Use

### 1. Add a Camera

1. Click **Add Camera** on the welcome screen (or right-click in the sidebar)
2. Enter a name for the camera
3. Select the reference image for that camera

The image is archived internally — you can delete or move the original file without affecting the app.

---

### 2. Draw an ROI

1. Select a camera in the sidebar
2. Click **+ Add ROI** on the camera detail page (or right-click the camera in the sidebar)
3. You are taken to the **Draw ROI** tab
4. Click on the image to place polygon vertices
5. Right-click to close the polygon (connect last point to first)
6. Give the ROI a name in the name field at the top
7. Click **Save ROI**

**Controls on the canvas:**

| Action | Result |
|---|---|
| Left-click | Add a vertex |
| Right-click | Close the polygon |
| `Ctrl+Z` | Undo last vertex |
| `Escape` | Clear all vertices |

---

### 3. Visualize an ROI

1. Open an existing ROI from the sidebar or camera detail page
2. Switch to the **Visualize ROI** tab
3. The saved polygon is automatically loaded onto the image
4. You can also paste coordinates manually into the input box and click **Visualize**

---

### 4. Edit or Delete an ROI

- **Edit** — Open the ROI from the sidebar or the camera detail card, modify the polygon or name, then click **Save ROI**
- **Delete** — Right-click the ROI in the sidebar and select **Delete ROI**

---

### 5. Manage Cameras

Right-click any camera in the sidebar for options:

- **Add ROI**
- **Rename Camera**
- **Delete Camera** (also removes all its ROIs)

---

## Coordinate Formats

When saving an ROI from the **Draw ROI** tab, use the format dropdown to select how coordinates are exported:

| Format | Description | Example |
|---|---|---|
| **JSON Array** | Standard JSON list of `[x, y]` pairs | `[[120, 340], [500, 210]]` |
| **Python Literal** | Python-style tuple list | `[(120, 340), (500, 210)]` |
| **Corner JSON** | Named corners: `tl`, `tr`, `br`, `bl` | See below |
| **Space-separated** | One `x y` pair per line | `120 340\n500 210` |
| **Flat CSV** | Comma-separated flat list | `120, 340, 500, 210` |

**Corner JSON** (useful for 4-point vehicle detection configs):

```json
{
    "roi": {
        "tl": {"x": 0.12, "y": 0.34},
        "tr": {"x": 0.56, "y": 0.34},
        "br": {"x": 0.56, "y": 0.78},
        "bl": {"x": 0.12, "y": 0.78}
    }
}
```

**Normalize coordinates** — check the **Normalize** box to output values between `0.0` and `1.0` (x divided by image width, y divided by image height). Useful for resolution-independent configs.

---

## Visualize Input Formats

The **Visualize ROI** tab accepts all of the above formats automatically — paste any of them and click **Visualize**.

---

## Data Storage

All data is saved automatically to:

```
~/.roi_tool/
├── cameras.json      # Camera and ROI metadata
└── images/           # Archived copies of camera reference images
```

- Data persists across sessions automatically — no manual save needed
- Images are copied into `~/.roi_tool/images/` when a camera is added, so moving or deleting the original file has no effect
- To fully reset the app, delete the `~/.roi_tool/` directory

---

## Building from Source

The build scripts handle everything automatically.

### Windows

Requirements: Python 3.9+ installed with "Add to PATH" checked.

```
Double-click build_windows.bat
```

The script will:
1. Create an isolated virtual environment (`build_env/`)
2. Install PyQt5, Pillow, and PyInstaller
3. Build `dist/ROITool.exe`
4. Open the `dist/` folder when complete

### Linux

Requirements: Python 3.9+ and `python3-venv`.

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Output: `dist/ROITool`

---

## Tech Stack

| Component | Technology |
|---|---|
| GUI framework | PyQt5 |
| Image processing | Pillow (PIL) |
| Data persistence | JSON (atomic writes) |
| Packaging | PyInstaller |
| Language | Python 3.9+ |

---

## Project Structure

```
draw_vis_roi/
├── app.py               # Main application (single file)
├── requirements.txt     # Python dependencies
├── roi_tool.spec        # PyInstaller build spec
├── build_windows.bat    # Windows build script (double-clickable)
├── build_linux.sh       # Linux build script
└── README.md            # This file
```
