"""Local Windows assistant with a guarded Telegram chat-read/reply workflow.

Example: "прочитай чат с Даней и ответь ему". The app searches Telegram,
reads the selected chat using a local Ollama vision model, previews the draft,
and sends only after a separate confirmation. It refuses to type into modal dialogs.
"""

import base64
import ctypes
import json
import os
import re
import tempfile
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

import ai_assistant as assistant


def chat_reply_contact(text):
    """Extract the recipient from a natural-language read-chat/reply request."""
    if not re.search(r"(?:прочитай|почитай|посмотри|глянь)", text, re.I):
        return None
    if not re.search(r"(?:чат|переписк\w*|сообщени\w*)", text, re.I):
        return None
    if not re.search(r"(?:ответь|напиши|предложи|составь)", text, re.I):
        return None
    match = re.search(
        r"(?:чат|переписк\w*|сообщени\w*)\s+(?:с|у)\s+(.+?)"
        r"(?=\s*,?\s*(?:и\s+)?(?:ответь|напиши|предложи|составь)\b|[.!?]|$)",
        text, re.I,
    )
    return match.group(1).strip(" \t\r\n,;:«»\"'") if match else None


class ClaudeStyleApp(assistant.App):
    """Use one natural-language request and guard all Telegram keyboard input."""

    def __init__(self, root):
        super().__init__(root)

        for child in root.winfo_children():
            child.destroy()

        root.title("Локальный агент · Claude Code style")
        root.geometry("1440x900")
        root.minsize(1180, 700)
        root.configure(bg="#0b111c")

        self._telegram_hwnd = None

        shell = tk.Frame(root, bg="#0b111c")
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg="#111b2b", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        title_bar = tk.Frame(shell, bg="#0d1726")
        title_bar.pack(side="top", fill="x")

        left_btn = tk.Button(sidebar, text="☰", bg="#111b2b", fg="#d8e3f1", bd=0, relief="flat", anchor="w", padx=14, pady=10)
        left_btn.pack(side="top", fill="x")

        search = tk.Entry(sidebar, bg="#1a2436", fg="#dfeaf7", insertbackground="#dfeaf7", bd=0, relief="flat", font=("Segoe UI", 12))
        search.insert(0, "Поиск")
        search.pack(fill="x", padx=14, pady=(10, 12))

        contacts = [
            ("Архив", "#8aa4c4"),
            ("Еката", "#5bc0be"),
            ("Ня", "#f4d35e"),
            ("Даня", "#ef476f"),
            ("Трейд", "#7bdff2"),
            ("Юльяна", "#ff9f1c"),
        ]
        for name, color in contacts:
            row = tk.Frame(sidebar, bg="#111b2b")
            row.pack(fill="x", padx=10, pady=4)
            dot = tk.Label(row, text="●", fg=color, bg="#111b2b", font=("Segoe UI", 12), width=2)
            dot.pack(side="left")
            label = tk.Label(row, text=name, fg="#dfeaf7", bg="#111b2b", font=("Segoe UI", 11), anchor="w")
            label.pack(side="left", fill="x", expand=True)

        sidebar_bottom = tk.Frame(sidebar, bg="#111b2b")
        sidebar_bottom.pack(side="bottom", fill="x", padx=10, pady=12)
        tk.Label(sidebar_bottom, text="Вася", fg="#dfeaf7", bg="#111b2b", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        chat_area = tk.Frame(shell, bg="#0d1726")
        chat_area.pack(side="left", fill="both", expand=True)

        top_line = tk.Frame(chat_area, bg="#111d2d", height=64)
        top_line.pack(fill="x")
        top_line.pack_propagate(False)
        tk.Label(top_line, text="Обсуждение", fg="#e8edf7", bg="#111d2d", font=("Segoe UI", 17, "bold")).pack(side="left", padx=18, pady=16)

        toolbar = tk.Frame(chat_area, bg="#101b2a")
        toolbar.pack(fill="x", padx=0, pady=0)

        self.level_box = ttk.Combobox(toolbar, values=assistant.LEVELS, state="readonly", width=10)
        self.level_box.current(1)
        self.level_box.pack(side="left", padx=(12, 8), pady=10)

        tk.Label(toolbar, text="Модель:", bg="#101b2a", fg="#a9b9cf", font=("Segoe UI", 10)).pack(side="left")
        self.model_box = ttk.Combobox(toolbar, values=[], state="readonly", width=16, postcommand=self.refresh_models)
        self.model_box.pack(side="left", padx=(8, 8), pady=10)
        self.model_box.bind("<<ComboboxSelected>>", self.on_model)

        cb = dict(bg="#101b2a", fg="#dfeaf7", selectcolor="#1d2d40", activebackground="#101b2a", activeforeground="#ffffff", bd=0)
        self.agent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(toolbar, text="Агент", variable=self.agent_var, **cb).pack(side="left", padx=(8, 0), pady=10)
        self.full_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="Весь ПК", variable=self.full_var, **cb).pack(side="left", padx=(8, 0), pady=10)

        self.ask_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="подтверждать правки", variable=self.ask_var, **cb).pack(side="left", padx=(8, 0), pady=10)

        self.ws_label = tk.Label(toolbar, text="", bg="#101b2a", fg="#9fb1c9", anchor="w", font=("Segoe UI", 9))
        self.ws_label.pack(side="right", padx=(8, 12), pady=10)

        self.status = tk.Label(chat_area, text="", bg="#0d1726", fg="#d5deee", anchor="w", font=("Segoe UI", 9))
        self.status.pack(fill="x", padx=12)

        self.log = scrolledtext.ScrolledText(chat_area, bg="#101c2a", fg="#e7edf8", font=("Segoe UI", 11), wrap="word", state="disabled",
                                            bd=0, highlightthickness=0, insertbackground="#ffffff")
        self.log.pack(fill="both", expand=True, padx=12, pady=(8, 6))
        self.log.tag_config("me", foreground="#72c6ff")
        self.log.tag_config("ai", foreground="#dfeaf7")
        self.log.tag_config("sys", foreground="#9bb0c8")
        self.log.tag_config("think", foreground="#7a879b", font=("Segoe UI", 10, "italic"))
        self.log.tag_config("code", foreground="#ffd27a", font=("Consolas", 10))

        input_bar = tk.Frame(chat_area, bg="#0d1726")
        input_bar.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(input_bar, bg="#1b2433", fg="#edf4ff", insertbackground="#edf4ff", font=("Segoe UI", 11), bd=0,
                              relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=12)
        self.entry.bind("<Return>", self.send)
        self.entry.focus_set()

        self.stop_btn = tk.Button(input_bar, text="Стоп", command=self.on_stop, state="disabled", bg="#d9534f", fg="white",
                                  bd=0, padx=18, pady=8, font=("Segoe UI", 10, "bold"))
        self.stop_btn.pack(side="right", padx=(10, 0))

        if assistant.TkinterDnD:
            try:
                for w in (self.log, self.entry):
                    w.drop_target_register(assistant.DND_FILES)
                    w.dnd_bind("<<Drop>>", self.on_drop)
            except Exception:
                pass

        self.q = assistant.queue.Queue()
        self.stop = threading.Event()
        self.history, self.last = [], None
        self.busy = False
        self.model_shown = False
        self.load()
        self.apply_settings()
        self.say("Пиши свободно: вопросы, команды, файлы, код и Telegram-переписки. /clear очистит историю. /undo вернёт последнюю правку.", "sys", log=False)
        if self.history:
            self.say(f"Загружена история: {len(self.history)} сообщений. Последние 30 показаны ниже.", "sys", log=False)
            for m in self.history[-30:]:
                mine = m["role"] == "user"
                self.say(("Ты: " if mine else "ИИ: ") + m["content"][:1200], "me" if mine else "ai", log=False)
        self.root.after(100, self.poll)

    def work(self):
        text = getattr(self, "cur_text", "")
        contact = chat_reply_contact(text)
        if not contact:
            return super().work()
        try:
            self._read_and_reply_telegram(contact, text)
        except Exception as exc:
            self.q.put(("msg", f"Сценарий Telegram остановлен: {exc}. Ничего не отправлено.", "sys"))
        finally:
            self.save()
            self.q.put(("done",))


def main():
    root = assistant.TkinterDnD.Tk() if assistant.TkinterDnD else tk.Tk()
    ClaudeStyleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
