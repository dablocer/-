"""Launch the original local assistant interface.

This file intentionally leaves the UI layout to ai_assistant.App. It does not
create a fake Telegram sidebar or replace the assistant with a mock chat screen.
Run with: python claude_style.py
"""

import tkinter as tk

import ai_assistant as assistant


def main():
    root = assistant.TkinterDnD.Tk() if assistant.TkinterDnD else tk.Tk()
    assistant.App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
