# File I/O operations and path utilities.

import os

# Μέγιστο επιτρεπόμενο μέγεθος αρχείου (200 MB)
MAX_FILE_SIZE = 200 * 1024 * 1024


def read_file(path: str) -> bytes:
    # Read binary file, raise IOError on failure. Raises ValueError if file exceeds MAX_FILE_SIZE
    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large ({size} bytes). Maximum allowed is {MAX_FILE_SIZE} bytes.")
    with open(path, 'rb') as f:
        return f.read()


def write_file(path: str, data: bytes) -> None:
    # Write binary file, raise IOError on failure.
    with open(path, 'wb') as f:
        f.write(data)


def get_extension(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def extension_to_format(ext: str) -> str:
    mapping = {
        '.jpg': 'JPEG', '.jpeg': 'JPEG',
        '.png': 'PNG',
        '.bmp': 'BMP',
        '.gif': 'GIF',
        '.tiff': 'TIFF', '.tif': 'TIFF',
        '.webp': 'WEBP',
        '.ppm': 'PPM',
        '.tga': 'TGA',
    }
    return mapping.get(ext, '')