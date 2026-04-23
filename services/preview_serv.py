# preview

from PIL import Image, ImageTk, UnidentifiedImageError
import io
import logging

logger = logging.getLogger(__name__)


def generate_image_preview(data: bytes, max_size: tuple = (560, 560)):
    #"""Convert raw image bytes to a PhotoImage thumbnail. Returns (PhotoImage, None) on success, (None, error_message) on failure.
    try:
        img = Image.open(io.BytesIO(data))
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        # Convert to RGBA if necessary for tkinter
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA')
        return ImageTk.PhotoImage(img), None
    except UnidentifiedImageError:
        msg = "Unidentified image format (file may be corrupted or not an image)"
        logger.debug(f"Preview failed: {msg}")
        return None, msg
    except Exception as e:
        msg = f"Preview error: {e}"
        logger.exception("Preview generation failed")
        return None, msg