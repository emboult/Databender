import tkinter as tk
from PIL import ImageFile
from model.state import AppState
from model.history import History
from viewers.editor_v import EditorView
from controllers.editor_con import EditorController

try:
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    pass



def main():
    root = tk.Tk()
    root.title("Databender")
    root.geometry("1200x700")

    state = AppState()
    history = History()
    view = EditorView(root)
    view.pack(fill="both", expand=True)

    controller = EditorController(state, history, view)
    view.bind_controller(controller)

    root.mainloop()


if __name__ == "__main__":
    main()