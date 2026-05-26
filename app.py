import io

import av
import cv2
import numpy as np
import qrcode
import streamlit as st
from PIL import Image
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q
from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer

ERROR_LEVELS = {
    "Low (~7%)": ERROR_CORRECT_L,
    "Medium (~15%)": ERROR_CORRECT_M,
    "Quartile (~25%)": ERROR_CORRECT_Q,
    "High (~30%)": ERROR_CORRECT_H,
}

DECODE_UPLOAD = "Upload image"
DECODE_CAMERA = "Camera scan"
CAMERA_WEBRTC_KEY = "qr-decode-camera"


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def decode_qr_from_image(image: Image.Image) -> list[str]:
    bgr = pil_to_bgr(image)
    detector = cv2.QRCodeDetector()
    ok, texts, _, _ = detector.detectAndDecodeMulti(bgr)
    if ok and texts is not None:
        found = [text for text in texts if text]
        if found:
            return found
    text, _, _ = detector.detectAndDecode(bgr)
    return [text] if text else []


def show_decoded_messages(messages: list[str]) -> None:
    if not messages:
        st.warning("No QR code found in this image. Try a clearer photo with good lighting.")
        return

    st.subheader("Decoded message")
    for index, message in enumerate(messages, start=1):
        if len(messages) > 1:
            st.caption(f"QR code {index}")
        st.success(message)
        st.code(message, language=None)


def make_qr_image(
    data: str,
    *,
    box_size: int,
    border: int,
    error_correction,
    fill_color: str,
    back_color: str,
) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill_color, back_color=back_color).get_image()


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class QRVideoProcessor(VideoProcessorBase):
    def __init__(self) -> None:
        self.decoded: str | None = None
        self.detector = cv2.QRCodeDetector()

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        data, _, _ = self.detector.detectAndDecode(img)
        if data:
            self.decoded = data
        return frame


def render_page_header(title: str, description: str) -> None:
    st.title(title)
    st.caption(description)
    st.divider()


def render_encode_page() -> None:
    render_page_header(
        "Create QR code",
        "Turn a URL, contact detail, Wi-Fi password, or short note into a downloadable PNG.",
    )

    left, right = st.columns([1.05, 0.95], gap="large", vertical_alignment="top")

    with left:
        with st.container(border=True):
            content = st.text_area(
                "Content",
                placeholder="https://example.com or any text",
                height=160,
                key="qr_content",
            )

            with st.popover("QR settings", width="stretch"):
                box_size = st.slider("Module size", min_value=4, max_value=20, value=10)
                border = st.slider("Quiet zone", min_value=1, max_value=10, value=4)
                error_label = st.selectbox(
                    "Error correction",
                    options=list(ERROR_LEVELS.keys()),
                    index=1,
                )
                color_cols = st.columns(2)
                fill_color = color_cols[0].color_picker("Foreground", "#111827")
                back_color = color_cols[1].color_picker("Background", "#ffffff")

            if st.button("Generate QR code", type="primary", width="stretch"):
                if content.strip():
                    st.session_state.generated_qr_content = content.strip()
                else:
                    st.session_state.pop("generated_qr_content", None)

            st.caption(f"{len(content.strip())} character(s) ready to encode.")

    with right:
        with st.container(border=True, horizontal_alignment="center"):
            generated_content = st.session_state.get("generated_qr_content", "")

            if not generated_content:
                st.info("Type something, then tap **Generate QR code**.")
                st.stop()

            image = make_qr_image(
                generated_content,
                box_size=box_size,
                border=border,
                error_correction=ERROR_LEVELS[error_label],
                fill_color=fill_color,
                back_color=back_color,
            )

            st.image(image, caption="Preview", width="stretch")

            png_bytes = image_to_png_bytes(image)
            st.download_button(
                label="Download PNG",
                data=png_bytes,
                file_name="qrcode.png",
                mime="image/png",
                type="primary",
                width="stretch",
            )


def render_upload_decode() -> None:
    st.subheader("Upload image")

    with st.container(border=True):
        uploaded = st.file_uploader(
            "Image",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            help="PNG, JPEG, WebP, and BMP files are supported.",
        )

    if uploaded is None:
        st.info("Upload an image that contains a QR code.")
        return

    image = Image.open(uploaded)
    col_image, col_result = st.columns([1, 1], gap="large", vertical_alignment="top")
    with col_image:
        with st.container(border=True):
            st.image(image, caption="Uploaded image", width="stretch")
    with col_result:
        with st.container(border=True):
            show_decoded_messages(decode_qr_from_image(image))


@st.fragment(run_every=0.5)
def poll_camera_decode() -> None:
    if st.session_state.get("camera_scan_complete"):
        return
    ctx = st.session_state.get(CAMERA_WEBRTC_KEY)
    if ctx is None or not getattr(ctx, "video_processor", None):
        return
    decoded = ctx.video_processor.decoded
    if not decoded:
        return
    st.session_state.camera_decoded_text = decoded
    st.session_state.camera_scan_complete = True
    st.rerun()


def render_camera_decode() -> None:
    st.subheader("Camera scan")

    scan_complete = st.session_state.get("camera_scan_complete", False)

    with st.container(border=True):
        st.caption(
            "Allow camera access and point at a QR code. Scanning stops automatically "
            "when a code is read."
        )

        if scan_complete and st.button("Scan again", type="primary"):
            st.session_state.camera_scan_complete = False
            st.session_state.pop("camera_decoded_text", None)
            st.rerun()

        ctx = webrtc_streamer(
            key=CAMERA_WEBRTC_KEY,
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"video": True, "audio": False},
            video_processor_factory=QRVideoProcessor,
            async_processing=True,
            desired_playing_state=False if scan_complete else None,
        )

    if scan_complete:
        with st.container(border=True):
            show_decoded_messages([st.session_state.camera_decoded_text])
            st.caption("Scanning stopped.")
        return

    if not ctx.state.playing:
        st.info("Press **Start** above to turn on the camera.")
    else:
        st.caption("Scanning... hold the QR code steady in view.")
        poll_camera_decode()


def render_decode_page() -> None:
    render_page_header(
        "Decode QR code",
        "Read one or more QR codes from an uploaded image or a live camera scan.",
    )

    source = st.segmented_control(
        "Input",
        [DECODE_UPLOAD, DECODE_CAMERA],
        default=DECODE_UPLOAD,
        label_visibility="hidden",
    )

    if source == DECODE_UPLOAD:
        render_upload_decode()
    else:
        render_camera_decode()


def main() -> None:
    st.set_page_config(page_title="QR Code Tools", layout="wide")

    pages = [
        st.Page(render_encode_page, title="Create", icon=":material/qr_code_2:", default=True),
        st.Page(render_decode_page, title="Decode", icon=":material/center_focus_strong:"),
    ]
    st.navigation(pages, position="top").run()


main()
