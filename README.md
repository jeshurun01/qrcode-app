# QR Code Tools

A small [Streamlit](https://streamlit.io/) app to create QR codes from text and decode QR codes from images or your camera.

## Setup

Requires [uv](https://docs.astral.sh/uv/). From this directory:

```bash
uv sync
```

## Run

```bash
uv run streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501).

## Features

**Create QR code**
- Encode any text or URL
- Adjust module size, quiet zone, and error correction from the settings popover
- Customize foreground and background colors
- Preview and download as PNG

**Decode QR code**
- Upload or drop an image (PNG, JPEG, WebP, BMP)
- Live camera scan — press **Start**, point at a QR code; scanning stops when a code is read (use **Scan again** to rescan)

The app uses modern Streamlit navigation, segmented controls, popovers, bordered containers, and fragments for camera polling.

Camera scanning uses your browser webcam. Allow camera permissions when prompted. On some networks you may need to open the app on `localhost` for the camera to work.
