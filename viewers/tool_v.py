# ask params for each tool, using a common dialog class

from viewers.tool_dialog import ToolDialog


def ask_whitespace_params(parent, tool_name: str, preview_callback=None, file_size=0):
    dialog = ToolDialog(
        parent=parent,
        tool_name=tool_name,
        title="Whitespace Inject",
        parameters=[
            {
                'name': 'count',
                'label': 'Number of whitespace bytes to insert:',
                'type': 'slider',
                'min': 1,
                'max': 6400,
                'default': 16
            }
        ],
        preview_callback=preview_callback,
        file_size=file_size
    )
    return dialog.show()


def ask_repeat_chunks_params(parent, tool_name: str, preview_callback=None, file_size=0):
    dialog = ToolDialog(
        parent=parent,
        tool_name=tool_name,
        title="Repeat Chunks",
        parameters=[
            {
                'name': 'size',
                'label': 'Chunk size (bytes):',
                'type': 'slider',
                'min': 1,
                'max': 6400,
                'default': 16
            },
            {
                'name': 'repeats',
                'label': 'Repeat count:',
                'type': 'slider',
                'min': 1,
                'max': 5000,
                'default': 2
            }
        ],
        preview_callback=preview_callback,
        file_size=file_size
    )
    return dialog.show()


def ask_pattern_inject_params(parent, tool_name: str, preview_callback=None, file_size=0):
    dialog = ToolDialog(
        parent=parent,
        tool_name=tool_name,
        title="Pattern Inject",
        parameters=[
            {
                'name': 'pattern',
                'label': 'Hex pattern (e.g. CA FE B0 D1):',
                'type': 'hex_entry',
                'default': ''
            },
            {
                'name': 'count',
                'label': 'Insert count:',
                'type': 'slider',
                'min': 1,
                'max': 100,
                'default': 10,
                'step': 1
            }
        ],
        preview_callback=preview_callback,
        file_size=file_size
    )
    return dialog.show()


def ask_shuffle_blocks_params(parent, tool_name: str, preview_callback=None, file_size=0):
    dialog = ToolDialog(
        parent=parent,
        tool_name=tool_name,
        title="Shuffle Blocks",
        parameters=[
            {
                'name': 'block_size',
                'label': 'Block size:',
                'type': 'slider',
                'min': 1,
                'max': 64000,
                'default': 16
            }
        ],
        preview_callback=preview_callback,
        file_size=file_size
    )
    return dialog.show()


def ask_hex_pattern_replace_params(parent, tool_name: str, preview_callback=None, file_size=0):
    dialog = ToolDialog(
        parent=parent,
        tool_name=tool_name,
        title="Hex Pattern Replace",
        parameters=[
            {
                'name': 'pattern',
                'label': 'Enter hex pattern (e.g. ff..00):',
                'type': 'entry',
                'default': ''
            },
            {
                'name': 'replace',
                'label': 'Enter replacement (e.g. 000000):',
                'type': 'hex_entry',
                'default': ''
            }
        ],
        preview_callback=preview_callback,
        file_size=file_size
    )
    return dialog.show()


def ask_reverse_blocks_params(parent, tool_name: str, preview_callback=None, file_size=0):
    dialog = ToolDialog(
        parent=parent,
        tool_name=tool_name,
        title="Reverse Blocks",
        parameters=[
            {
                'name': 'block_size',
                'label': 'Block size in bytes:',
                'type': 'slider',
                'min': 1,
                'max': 6400,
                'default': 16
            }
        ],
        preview_callback=preview_callback,
        file_size=file_size
    )
    return dialog.show()