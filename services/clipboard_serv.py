import pyperclip


def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard using pyperclip.

    Raises:
        RuntimeError: if clipboard access fails.
    """
    try:
        pyperclip.copy(text)
    except Exception as e:
        raise RuntimeError(f"Could not copy to clipboard: {e}") from e


def paste_from_clipboard() -> str:
    """Retrieve text from system clipboard using pyperclip.

    Raises:
        RuntimeError: if clipboard access fails.
    """
    try:
        return pyperclip.paste()
    except Exception as e:
        raise RuntimeError(f"Could not paste from clipboard: {e}") from e


def parse_hex(hex_str: str) -> bytes:
    """Convert a hex string (with optional spaces) to bytes.

    Raises:
        ValueError: if the hex string is invalid.
    """
    cleaned = hex_str.replace(" ", "").replace("\n", "").replace("\r", "")
    if len(cleaned) % 2 != 0:
        raise ValueError("Hex string length must be even")
    return bytes.fromhex(cleaned)