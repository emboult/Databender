import io
from typing import Optional, Callable, Any, Dict

# Προαιρετικό import για το Pillow (αν δεν υπάρχει, απλά δεν κάνουμε register τα image codecs)
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# =====================================================================
# ΣΤΑΘΕΡΕΣ ΚΑΙ ΠΙΝΑΚΕΣ ΜΕΤΑΦΡΑΣΗΣ
# =====================================================================


# Translation table used to produce a single-column-per-byte Latin-1 rendering
_TRANS_TABLE_BYTES = []
for i in range(256):
    if (0x20 <= i <= 0x7E) or (0xA0 <= i <= 0xFF):
        _TRANS_TABLE_BYTES.append(i)
    else:
        _TRANS_TABLE_BYTES.append(ord('.'))

TRANS_TABLE = bytes.maketrans(bytes(range(256)), bytes(_TRANS_TABLE_BYTES))

MAGIC_BYTES = {
    "JPEG": b'\xff\xd8\xff',
    "PNG": b'\x89PNG\r\n\x1a\n',
    "BMP": b'BM',
    "GIF": b'GIF8',
    "TIFF": b'II*\x00',
    "WEBP": b'RIFF'
}


# =====================================================================
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ BYTES & STRINGS
# =====================================================================

def printable_latin1_str(data: bytes) -> str:
    """Return a 1:1-width string for the Latin-1 column."""
    if not data:
        return ""
    try:
        return data.translate(TRANS_TABLE).decode("latin-1")
    except Exception:
        out = []
        for b in data:
            if (0x20 <= b <= 0x7E) or (0xA0 <= b <= 0xFF):
                out.append(chr(b))
            else:
                out.append('.')
        return ''.join(out)




# =====================================================================
# ΑΝΑΓΝΩΡΙΣΗ ΜΟΡΦΩΝ (FORMAT DETECTION)
# =====================================================================

def detect_format(data: bytes) -> str:
    if data.startswith(b'\xff\xd8\xff'):
        return "JPEG"
    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "PNG"
    elif data.startswith(b'BM'):
        return "BMP"
    elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return "GIF"
    elif data.startswith(b'II*\x00') or data.startswith(b'MM\x00*'):
        return "TIFF"
    elif len(data) > 12 and data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return "WEBP"
    elif len(data) >= 3:
        ppm_magic = data[:2]
        if ppm_magic in {b'P1', b'P2', b'P3', b'P4', b'P5', b'P6'}:
            if chr(data[2]) in ' \t\n\r':
                return "PPM"
    if len(data) >= 18:
        colormap_type = data[1]
        image_type = data[2]
        if colormap_type in {0, 1} and image_type in {1, 2, 3, 9, 10, 11}:
            colormap_len = int.from_bytes(data[5:7], 'little')
            if colormap_type == 0 and colormap_len != 0:
                pass
            else:
                pixel_depth = data[16]
                if pixel_depth in {8, 15, 16, 24, 32}:
                    img_descriptor = data[17]
                    reserved_bits = img_descriptor & 0xC0
                    alpha_bits = img_descriptor & 0x0F
                    if reserved_bits == 0 and alpha_bits <= 8:
                        return "TGA"
    return "Unknown"

def get_format_extension(format: str) -> str:
    ext_map = {
        "JPEG": ".jpg", 
        "PNG": ".png", 
        "BMP": ".bmp", 
        "GIF": ".gif", 
        "TIFF": ".tiff", 
        "WEBP": ".webp",
        "PPM": ".ppm",
        "TGA": ".tga"
    }
    return ext_map.get(format, ".bin")

def ensure_magic_bytes(data: bytes, fmt: Optional[str]) -> bytes:
    """Ensure `data` starts with the required magic/header bytes for `fmt`.
    If magic is missing, prepend it.
    """
    if not fmt or not data:
        return data
    key = fmt.upper()
    magic = MAGIC_BYTES.get(key)
    if magic and not data.startswith(magic):
        return magic + data
    return data


# =====================================================================
# CODEC REGISTRY
# =====================================================================

CodecDecoder = Callable[[bytes, Optional[str]], Any]
CodecEncoder = Callable[[Any, str], bytes]

_DECODERS: Dict[str, CodecDecoder] = {}
_ENCODERS: Dict[str, CodecEncoder] = {}

def register_codec(format_name: str, decoder: CodecDecoder, encoder: CodecEncoder):
    _DECODERS[format_name.upper()] = decoder
    _ENCODERS[format_name.upper()] = encoder

def decode_bytes(data: bytes, fmt: Optional[str] = None, mode: str = "raw") -> Any:
    if fmt:
        key = fmt.upper()
        dec = _DECODERS.get(key)
        if dec is not None:
            return dec(data, mode)

    if mode == "raw":
        return bytes(data)
    if mode == "image":
        if not HAS_PILLOW:
            raise RuntimeError("Pillow is required for image decode")
        return Image.open(io.BytesIO(data)).convert("RGBA")

    raise ValueError(f"Unsupported decode mode: {mode}")

def encode_bytes(obj: Any, target_format: str, mode: str = "raw") -> bytes:
    key = target_format.upper() if target_format else ""
    enc = _ENCODERS.get(key)
    if enc is not None:
        return enc(obj, target_format)

    if mode == "raw":
        if isinstance(obj, (bytes, bytearray)):
            return bytes(obj)
        raise ValueError("raw mode expects bytes-like object")

    if mode == "image":
        if not HAS_PILLOW:
            raise RuntimeError("Pillow is required for image encode")
        if not hasattr(obj, "save"):
            raise ValueError("image mode expects a Pillow Image-like object")
        buf = io.BytesIO()
        fmt = target_format.upper() if target_format else "PNG"
        obj.save(buf, format=fmt)
        return buf.getvalue()

    raise ValueError(f"Unsupported encode mode: {mode}")


# =====================================================================
# DEFAULT CODEC INITIALIZATION
# =====================================================================

if HAS_PILLOW:
    def _image_decoder(data: bytes, mode: Optional[str]) -> Image.Image:
        return Image.open(io.BytesIO(data)).convert("RGBA")

    def _image_encoder(img: Image.Image, fmt: str) -> bytes:
        # Αν το format είναι JPEG και η εικόνα έχει διαφάνεια (mode RGBA), τη μετατρέπουμε σε RGB
        if fmt.upper() == 'JPEG' and img.mode == 'RGBA':
            img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()

    for _fmt in ("PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP", "PPM", "TGA"):
        register_codec(_fmt, _image_decoder, _image_encoder)