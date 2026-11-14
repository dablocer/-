"""Claude Code-inspired launcher for the existing local desktop assistant.

Run with: python claude_style.py
The assistant and all file/tool safety checks remain implemented in ai_assistant.py.
"""

import os
import random
import tkinter as tk
from tkinter import ttk

import ai_assistant as assistant


class ClaudeStyleApp(assistant.App):
    """Keep the existing agent, with a more focused coding-agent default UI."""

    def load(self):
        # Preserve saved preferences; use a more free, action-first setup on first launch.
        has_settings = os.path.isfile(assistant.HIST_FILE)
        super().load()
        if not has_settings:
            self.cfg.update(agent=True, full=True, ask=True)

    def __init__(self, root):
        super().__init__(root)
        root.title("Claude Code style · Локальный агент")
        root.geometry("1180x760")
        root.minsize(920, 560)
        root.configure(bg="#1b1b1b")

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground="#252525", background="#303030",
                        foreground="#eeeeee", arrowcolor="#eeeeee")
        style.map("TCombobox", fieldbackground=[("readonly", "#252525")],
                  foreground=[("readonly", "#eeeeee")])

        self.log.configure(bg="#1b1b1b", fg="#e7e5e4", insertbackground="#eeeeee",
                           padx=18, pady=14, font=("Segoe UI", 11), spacing1=4, spacing3=8)
        self.log.tag_config("me", foreground="#f4a261", font=("Segoe UI", 11, "bold"))
        self.log.tag_config("ai", foreground="#e7e5e4", font=("Segoe UI", 11))
        self.log.tag_config("sys", foreground="#a8a29e", font=("Segoe UI", 10))
        self.entry.configure(bg="#292524", fg="#f5f5f4", insertbackground="#f5f5f4",
                            font=("Segoe UI", 12), relief="flat", highlightthickness=1,
                            highlightbackground="#44403c", highlightcolor="#d97757")

        bar = tk.Frame(root, bg="#1b1b1b")
        bar.pack(side="top", fill="x", padx=12, pady=(8, 4), before=self.log)
        tk.Label(bar, text="Локальный агент", bg="#1b1b1b", fg="#f5f5f4",
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(bar, text="  ·  обычным языком, без команды " + chr(34) + "/" + chr(34) + " и без лишних вопросов",
                 bg="#1b1b1b", fg="#a8a29e", font=("Segoe UI", 10)).pack(side="left")
        tk.Button(bar, text="Новый чат", command=self._new_chat,
                  bg="#292524", fg="#e7e5e4", activebackground="#44403c", activeforeground="white",
                  bd=0, padx=10, pady=5, cursor="hand2").pack(side="right")

        quick = tk.Frame(root, bg="#1b1b1b")
        quick.pack(side="top", fill="x", padx=12, pady=(2, 8), before=self.log)
        tk.Label(quick, text="Попробуй:", bg="#1b1b1b", fg="#a8a29e",
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 7))

        self.prompt_examples = [
            ("Сделать скрин", "сделай скриншот экрана и сохрани в папку проекта"),
            ("Найти файл", "найди файл report.txt на компьютере и открой его"),
            ("Переместить", "перемести файл из документов в папку projects"),
            ("Скачать", "скачай этот файл в загрузки: https://example.com/file.zip"),
            ("Папка", "открой папку загрузки"),
            ("Telegram", "напиши @Mr_Dablocer в Telegram: привет, проверь проект"),
            ("Код", "создай Python проект-менеджер с окном и кнопками"),
            ("Случайно", ""),
        ]

        for label, prompt in self.prompt_examples:
            btn = tk.Button(
                quick,
                text=label,
                command=lambda p=prompt: self._insert_prompt(p) if p else self._insert_random_prompt(),
                bg="#292524",
                fg="#d6d3d1",
                activebackground="#44403c",
                activeforeground="white",
                bd=0,
                padx=9,
                pady=5,
                cursor="hand2",
            )
            btn.pack(side="left", padx=(0, 6))

        tk.Button(quick, text="Отправить", command=self.send, bg="#d97757", fg="#1c1917",
                  activebackground="#ea8a68", bd=0, padx=12, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")

        root.bind("<Control-l>", lambda _event: (self.entry.focus_set(), self.entry.select_range(0, "end")))
        root.bind("<Control-Return>", self.send)
        root.bind("<F1>", lambda _event: self._insert_random_prompt())

    def _insert_prompt(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.entry.focus_set()
        self.entry.icursor("end")

    def _insert_random_prompt(self):
        choices = [
            "сделай скриншот экрана и сохрани в папку проекта",
            "найди файл проекта по имени и открой его",
            "перемести документ из загрузок в рабочий стол",
            "создай простой Python-чатбот с кнопками в окне",
            "открой папку с документами и найди самый новый файл",
            "скачай файл по ссылке в загрузки и назови путь",
            "напиши @Mr_Dablocer в Telegram: проверил проект, всё готово",
            "сделай папку проекта с файлом notes.txt и запиши туда список задач",
        ]
        self._insert_prompt(random.choice(choices))

    def _new_chat(self):
        self.entry.delete(0, "end")
        self.history = []
        self.last = None
        self.save()
        self.say("История очищена.", "sys")


def main():
    root = assistant.TkinterDnD.Tk() if assistant.TkinterDnD else tk.Tk()
    ClaudeStyleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
