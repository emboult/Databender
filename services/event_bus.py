from blinker import Signal

file_loaded = Signal()               # emitted when a file is loaded
selection_changed = Signal()          # emitted when selection changes
status_message_requested = Signal()   # emitted to show a status message (arg: message)
preview_update_requested = Signal()   # emitted to update preview (arg: data)
state_modified = Signal()             # emitted after state modification
clear_highlights_requested = Signal() # emitted to clear change highlights