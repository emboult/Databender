#external view
import os
import sys
import tempfile
from model import formats

def open_in_viewer(data: bytes, fmt: str = None) -> None:
    #Write data to a temporary file and open with system default viewer.
  
    # Αν η μορφή είναι PPM ή TGA, κάνε μετατροπή σε PNG
    if fmt and fmt.upper() in ('PPM', 'TGA'):
        try:
            # Αποκωδικοποίηση σε εικόνα Pillow και επανακωδικοποίηση ως PNG
            img = formats.decode_bytes(data, fmt=fmt, mode='image')
            png_data = formats.encode_bytes(img, 'PNG', mode='image')
            data = png_data
            ext = '.png'
        except Exception as e:
            # Αν αποτύχει, χρησιμοποιούμε την αρχική μορφή
            print(f"Warning: could not convert {fmt} to PNG: {e}")
            ext = formats.get_format_extension(fmt)
    else:
        # Κανονική περίπτωση
        if fmt:
            ext = formats.get_format_extension(fmt)
        else:
            # Προσπάθεια ανίχνευσης από τα δεδομένα
            detected = formats.detect_format(data)
            ext = formats.get_format_extension(detected)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        if sys.platform.startswith("win"):
            os.startfile(tmp_path)
        elif sys.platform == "darwin":
            os.system(f"open '{tmp_path}'")
        else:
            os.system(f"xdg-open '{tmp_path}'")
    except Exception as e:
        # Σε περίπτωση σφάλματος, δεν διαγράφουμε το αρχείο για να μπορεί ο χρήστης να το βρει
        raise RuntimeError(f"Could not open viewer: {e}") from e