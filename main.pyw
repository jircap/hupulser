import tkinter as tk
from tkinter import ttk
from sys import platform as _platform
from hupulser_gui import HuPulserGui

if __name__ == "__main__":
    root = tk.Tk()
    # tk.Style().configure("TButton", padding=6, relief="flat", background="#ccc")
    # tk.Style.theme_use("default")
    s = ttk.Style()
    if _platform == "win32":
        s.theme_use("vista")
    elif _platform in ["linux", "linux2"]:
        s.theme_use("clam")
    elif _platform == "darwin":
        s.theme_use("aqua")

    app = HuPulserGui(root)
    root.configure(bg='#f5f5f5')
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
