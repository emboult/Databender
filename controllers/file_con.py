#File open/save/reload operations

from model import formats
from services import files_serv, dialog_serv
from services import event_bus
import os


class FileController:
    def __init__(self, state, view, history):
        self.state = state
        self.view = view
        self.history = history

    def _status(self, msg: str) -> None:
        event_bus.status_message_requested.send(self, message=msg)

    def _load_file(self, filename: str) -> bool:
        try:
            data = files_serv.read_file(filename)
        except ValueError as e:
            dialog_serv.show_error(self.view.master, str(e))
            return False
        except Exception as e:
            dialog_serv.show_error(self.view.master, f"Could not read file: {e}")
            return False

        fmt = formats.detect_format(data)
        self.state.load(filename, data, fmt)
        self.history.clear()
        event_bus.file_loaded.send(self)
        self._status(f"Opened {filename} ({len(data)} bytes as {fmt})")
        return True

    def on_open(self) -> None:
        parent = self.view.master
        filename = dialog_serv.ask_open_filename(
            parent=parent,
            title="Open image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ppm *.tga"), ("All files", "*.*")]
        )
        if not filename:
            self._status("Open cancelled")
            return
        self._load_file(filename)

    def on_save(self) -> None:
        parent = self.view.master
        suggested = ""
        if self.state.fname:
            base = self.state.fname
            if self.state.fmt:
                ext = formats.get_format_extension(self.state.fmt)
                base = base.rsplit('.', 1)[0] + ext
            suggested = base
        else:
            suggested = "glitched.png"

        fmt = self.state.fmt
        if fmt:
            ext = formats.get_format_extension(fmt).lstrip('.')
            filetypes = [(f"{fmt} files", f"*.{ext}"), ("All files", "*.*")]
            defaultextension = f".{ext}"
        else:
            filetypes = [("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            defaultextension = ".png"

        filename = dialog_serv.ask_save_filename(
            parent=parent,
            title="Save glitched image",
            initialfile=os.path.basename(suggested) if suggested else None,
            filetypes=filetypes,
            defaultextension=defaultextension
        )
        if not filename:
            return

        data = self.state.get_current_bytes()
        ext = files_serv.get_extension(filename).lower()
        target_fmt = files_serv.extension_to_format(ext)

        if target_fmt and target_fmt != self.state.fmt:
            try:
                data = self.state.encode(target_fmt, mode='image')
            except Exception as e:
                self._status(f"Conversion warning: {e}")

        data = formats.ensure_magic_bytes(data, target_fmt or self.state.fmt)

        try:
            files_serv.write_file(filename, data)
            self.state.original = data
            self._status(f"Saved as {filename} ({len(data)} bytes)")
        except Exception as e:
            dialog_serv.show_error(parent, f"Could not save file: {e}")

    def on_reload(self) -> None:
        if not self.state.fname or self.state.original is None:
            self._status("No file loaded")
            return

        if self.state.is_dirty():
            parent = self.view.master
            confirm = dialog_serv.ask_yesno(
                parent,
                "Reload original file? All unsaved changes will be lost.",
                title="Confirm Reload"
            )
            if not confirm:
                return

        self._load_file(self.state.fname)