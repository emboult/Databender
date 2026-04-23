# dialogs for tools
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable, Optional, List, Tuple
from services import resources

_TOOL_DESCRIPTIONS = resources.get_tool_descriptions()


class ToolDialog:
    def __init__(self, parent, tool_name: str, title: str, parameters: List[Dict[str, Any]],
                 preview_callback: Optional[Callable] = None, file_size: int = 0):
        """
        :param parent: parent window
        :param tool_name: tool identifier (for descriptions)
        :param title: dialog title
        :param parameters: list of parameter definitions, each with:
            - 'name': parameter name (for return dict)
            - 'label': display label
            - 'type': 'slider', 'entry', 'hex_entry'
            - 'min': min value (for slider)
            - 'max': max value (for slider)
            - 'default': default value
            - 'step': step for spinbox (optional)
        :param preview_callback: function to call for live preview
        :param file_size: file size for preview note
        """
        self.parent = parent
        self.tool_name = tool_name
        self.parameters = parameters
        self.preview_callback = preview_callback
        self.file_size = file_size
        self.result = None
        self.ok_clicked = False

        # Store variables
        self.vars = {}
        self.preview_job = None

        self._create_dialog(title)

    def _create_dialog(self, title: str):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(title)
        self.dialog.geometry("420x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self._center()

        # Add description section
        self._add_description_section()

        # Create main content frame
        self.content_frame = ttk.Frame(self.dialog)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create parameter widgets
        self._create_parameters()

        # Add preview checkbox if needed
        if self.preview_callback:
            self._add_preview_checkbox()

        # Add buttons
        self._add_buttons()

    def _center(self):
        self.dialog.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _add_description_section(self):
        desc = _TOOL_DESCRIPTIONS.get(self.tool_name, "")
        general_note = _TOOL_DESCRIPTIONS.get("general", "")
        
        if desc or general_note:
            # Container frame with border for visual separation
            desc_frame = ttk.LabelFrame(self.dialog, text="About this tool", padding=(10, 5))
            desc_frame.pack(fill="x", padx=10, pady=(10, 5))
            
            if desc: #description
                desc_label = ttk.Label(
                    desc_frame, 
                    text=desc, 
                    wraplength=380, 
                    justify="left",
                    font=("TkDefaultFont", 9)
                )
                desc_label.pack(fill="x", pady=(0, 5))
            
            if general_note: #general 
                note_label = ttk.Label(
                    desc_frame, 
                    text=general_note, 
                    font=("TkDefaultFont", 8, "italic"), 
                    foreground="gray", 
                    wraplength=380, 
                    justify="left"
                )
                note_label.pack(fill="x", pady=(5 if desc else 0, 0))

    def _create_parameters(self):
        for i, param in enumerate(self.parameters):
            param_frame = ttk.Frame(self.content_frame)
            param_frame.pack(fill="x", pady=5)

            # Label
            label = ttk.Label(param_frame, text=param['label'])
            label.pack(anchor="w")

            # Control frame (for slider + entry, etc.)
            control_frame = ttk.Frame(param_frame)
            control_frame.pack(fill="x", pady=(2, 0))

            # Create appropriate control based on type
            param_type = param.get('type', 'slider')
            var_name = param['name']

            if param_type in ('slider', 'spinbox'):
                var = tk.IntVar(value=param.get('default', 0))
                self.vars[var_name] = var

                # Slider
                if param_type == 'slider':
                    slider = ttk.Scale(
                        control_frame, from_=param['min'], to=param['max'],
                        variable=var, orient="horizontal", length=250, command=lambda val, v=var: v.set(int(float(val)))
                    )
                    slider.pack(side="left", padx=(0, 10))


                # Entry for numeric value
                entry = ttk.Entry(control_frame, textvariable=var, width=6)
                entry.pack(side="left")

            elif param_type == 'entry':
                var = tk.StringVar(value=param.get('default', ''))
                self.vars[var_name] = var
                entry = ttk.Entry(control_frame, textvariable=var, width=30)
                entry.pack(side="left")

            elif param_type == 'hex_entry':
                var = tk.StringVar(value=param.get('default', ''))
                self.vars[var_name] = var
                entry = ttk.Entry(control_frame, textvariable=var, width=30)
                entry.pack(side="left")

            # Bind trace for live preview
            if self.preview_callback:
                if param_type in ('slider', 'spinbox'):
                    var.trace('w', lambda *a: self._schedule_preview())
                elif param_type in ('entry', 'hex_entry'):
                    var.trace('w', lambda *a: self._schedule_preview())

    def _add_preview_checkbox(self):
        preview_frame = ttk.Frame(self.dialog)
        preview_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.preview_var = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(preview_frame, text="Live preview", variable=self.preview_var)
        cb.pack(side="left")

        # Add speed note based on file size
        if self.file_size > 50_000_000:  # > 50 MB
            note = "(disable for speed)"
            note_color = "orange"
        elif self.file_size > 10_000_000:  # 10–50 MB
            note = "(may be slow)"
            note_color = "gray"
        else:
            note = "(recommended)"
            note_color = "green"

        note_label = ttk.Label(
            preview_frame, 
            text=note, 
            foreground=note_color,
            font=("TkDefaultFont", 8, "italic")
        )
        note_label.pack(side="left", padx=(5, 0))

    def _add_buttons(self): #add ok/cancel
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side="left", padx=5)

    def _schedule_preview(self):
        #preview after 300ms
        if self.preview_job:
            self.dialog.after_cancel(self.preview_job)
        self.preview_job = self.dialog.after(300, self._do_preview)

    def _do_preview(self):
        if self.preview_var.get() and self.preview_callback:
            params = self.get_params()
            if params:
                self.preview_callback(params, enabled=True)
        elif self.preview_callback:
            self.preview_callback({}, enabled=False)

    def _on_ok(self):
        self.ok_clicked = True
        self.dialog.destroy()

    def _on_cancel(self):
        self.ok_clicked = False
        self.dialog.destroy()

    def get_params(self) -> Optional[Dict[str, Any]]:
        params = {}
        for param in self.parameters:
            var = self.vars[param['name']]
            value = var.get()

            # Validate based on type
            if param.get('type') == 'hex_entry':
                try:
                    # Clean and validate hex
                    cleaned = value.replace(' ', '').replace('\n', '').replace('\r', '')
                    if cleaned and len(cleaned) % 2 == 0:
                        # Store as bytes for pattern
                        params[param['name']] = bytes.fromhex(cleaned)
                    else:
                        return None  # Invalid hex
                except ValueError:
                    return None
            elif param.get('type') in ('slider', 'spinbox'):
                # Ensure within range
                min_val = param.get('min', 0)
                max_val = param.get('max', 100)
                try:
                    int_val = int(value)
                    if min_val <= int_val <= max_val:
                        params[param['name']] = int_val
                    else:
                        return None
                except (ValueError, TypeError):
                    return None
            elif param.get('type') == 'entry':
                # String parameter
                params[param['name']] = value
            else:
                # Default handling
                params[param['name']] = value

        return params

    def show(self) -> Optional[Dict[str, Any]]:
        self.dialog.wait_window()
        if self.ok_clicked:
            return self.get_params()
        return None