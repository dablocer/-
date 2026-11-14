"""Claude Code-inspired desktop assistant launcher.

Run with: python claude_style.py
The user opens the requested Telegram chat manually, then captures its visible window.
Images are sent only to the configured local Ollama model. This workflow drafts replies;
it does not send anything automatically.
"""

import os
import random
import tempfile
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import ai_assistant as assistant


BG = "#1b1b1b"
PANEL = "#292524"
ACCENT = "#d97757"


class ClaudeStyleApp(assistant.App):
    """A more focused UI with an explicit read-chat / draft-reply flow."""

    def load(self):
        has_settings = os.path.isfile(assistant.HIST_FILE)
        super().load()
        if not has_settings:
            self.cfg.update(agent=True, full=False, ask=True)

    def __init__(self, root):
        self.screen_attachments = set()
        self.pending_chat_contact = ""
        super().__init__(root)
        root.title("Локальный агент · Claude Code style")
        root.geometry("1180x760")
        root.minsize(900, 560)
        root.configure(bg=BG)

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground="#252525", background="#303030",
                        foreground="#eeeeee", arrowcolor="#eeeeee")
        style.map("TCombobox", fieldbackground=[("readonly", "#252525")],
                  foreground=[("readonly", "#eeeeee")])

        self.log.configure(bg=BG, fg="#e7e5e4", insertbackground="#eeeeee",
                           padx=18, pady=14, font=("Segoe UI", 11), spacing1=4, spacing3=8)
        self.log.tag_config("me", foreground="#f4a261", font=("Segoe UI", 11, "bold"))
        self.log.tag_config("ai", foreground="#e7e5e4", font=("Segoe UI", 11))
        self.log.tag_config("sys", foreground="#a8a29e", font=("Segoe UI", 10))
        self.entry.configure(bg=PANEL, fg="#f5f5f4", insertbackground="#f5f5f4",
                             font=("Segoe UI", 12), relief="flat", highlightthickness=1,
                             highlightbackground="#44403c", highlightcolor=ACCENT)

        header = tk.Frame(root, bg=BG)
        header.pack(side="top", fill="x", padx=12, pady=(8, 4), before=self.log)
        tk.Label(header, text="Локальный агент", bg=BG, fg="#f5f5f4",
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(header, text="  ·  обычным языком; перед отправкой сообщений будет подтверждение",
                 bg=BG, fg="#a8a29e", font=("Segoe UI", 10)).pack(side="left")
        tk.Button(header, text="Новый чат", command=self._new_chat, bg=PANEL, fg="#e7e5e4",
                  activebackground="#44403c", activeforeground="white", bd=0, padx=10,
                  pady=5, cursor="hand2").pack(side="right")

        actions = tk.Frame(root, bg=BG)
        actions.pack(side="top", fill="x", padx=12, pady=(2, 8), before=self.log)
        tk.Label(actions, text="Быстрые действия:", bg=BG, fg="#a8a29e",
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 7))
        self._button(actions, "Telegram: прочитать чат", self.start_telegram_read, "#c4b5fd")
        self._button(actions, "Прочитать активное окно", self.capture_active_window, "#93c5fd")
        self._button(actions, "Снимок экрана", self.capture_screen, "#f4a261")
        self._button(actions, "Читать ссылку", lambda: self._insert_prompt("прочитай страницу по ссылке: "))
        self._button(actions, "Переместить файл", lambda: self._insert_prompt("перемести файл из документов в "))
        self._button(actions, "Найти файл", lambda: self._insert_prompt("найди файл "))
        tk.Button(actions, text="Отправить", command=self.send, bg=ACCENT, fg="#1c1917",
                  activebackground="#ea8a68", bd=0, padx=12, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")

        tk.Label(root, text=("Telegram workflow: specify a contact → Telegram opens → select and verify the chat yourself → "
                             "capture the visible window → ask for a draft. Sending always requires a separate confirmation."),
                 bg=BG, fg="#a8a29e", anchor="w", justify="left", wraplength=1100,
                 font=("Segoe UI", 9)).pack(side="top", fill="x", padx=14, pady=(0, 4), before=self.log)

        root.bind("<Control-l>", lambda _event: (self.entry.focus_set(), self.entry.select_range(0, "end")))
        root.bind("<Control-Return>", self.send)
        root.bind("<F1>", lambda _event: self._insert_random_prompt())

    @staticmethod
    def _button(parent, text, command, fg="#d6d3d1"):
        tk.Button(parent, text=text, command=command, bg=PANEL, fg=fg,
                  activebackground="#44403c", activeforeground="white", bd=0,
                  padx=8, pady=5, cursor="hand2").pack(side="left", padx=(0, 5))

    def _insert_prompt(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.entry.focus_set()
        self.entry.icursor("end")

    def _insert_random_prompt(self):
        examples = [
            "сделай скриншот экрана и опиши, что на нём",
            "найди файл отчёт.txt в загрузках и открой его",
            "перемести документ из документов на рабочий стол",
            "прочитай эту страницу и кратко перескажи: https://example.com",
            "открой Telegram, найди чат с Даней и прочитай видимые последние сообщения",
            "создай папку проекта и запиши список задач в notes.txt",
        ]
        self._insert_prompt(random.choice(examples))

    def start_telegram_read(self):
        """Open Telegram, but leave contact selection to the user to avoid wrong-recipient actions."""
        contact = simpledialog.askstring("Telegram", "Какой чат открыть? (имя или @username)", parent=self.root)
        if not contact or not contact.strip():
            return
        self.pending_chat_contact = contact.strip()
        ok, message = assistant.run_action("open_app", "telegram", self.confirm)
        if not ok:
            messagebox.showerror("Telegram", message, parent=self.root)
            return
        self.say(f"{message} Найди и проверь чат «{self.pending_chat_contact}» в Telegram, затем нажми «Прочитать активное окно».", "sys")
        self._insert_prompt(
            f"Прочитай прикреплённый снимок окна Telegram. Я ищу чат «{self.pending_chat_contact}». "
            "Сначала скажи, какое имя чата видно, затем кратко перескажи только видимые последние сообщения и предложи черновик ответа. "
            "Не отправляй сообщение и не утверждай, что это нужный чат, если заголовок не читается."
        )
        messagebox.showinfo(
            "Выбери чат вручную",
            f"Telegram открыт. Сам выбери чат «{self.pending_chat_contact}» и проверь имя в заголовке.\n\n"
            "После этого вернись сюда и нажми «Прочитать активное окно». Ассистент увидит только снимок видимой части окна. "
            "Сообщение будет только предложено как черновик; отправки не будет.",
            parent=self.root,
        )

    @staticmethod
    def _powershell_capture(path, active_window=False):
        """Capture the foreground window or virtual desktop using built-in Windows APIs."""
        escaped = path.replace("'", "''")
        if active_window:
            script = r'''$src = @"
using System;
using System.Runtime.InteropServices;
public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
public static class WinCapture {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
"@; Add-Type -TypeDefinition $src; Add-Type -AssemblyName System.Drawing; $h=[WinCapture]::GetForegroundWindow(); $r=New-Object RECT; if ($h -eq [IntPtr]::Zero -or -not [WinCapture]::GetWindowRect($h,[ref]$r)) { throw 'No foreground window' }; $w=$r.Right-$r.Left; $hh=$r.Bottom-$r.Top; if ($w -le 0 -or $hh -le 0) { throw 'Window is minimized or has invalid size' }; $b=New-Object System.Drawing.Bitmap($w,$hh); $g=[System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($r.Left,$r.Top,0,0,$b.Size); $b.Save('__OUT__',[System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $b.Dispose()'''
        else:
            script = r'''Add-Type -AssemblyName System.Windows.Forms,System.Drawing; $s=[System.Windows.Forms.SystemInformation]::VirtualScreen; $b=New-Object System.Drawing.Bitmap($s.Width,$s.Height); $g=[System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($s.Left,$s.Top,0,0,$b.Size); $b.Save('__OUT__',[System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $b.Dispose()'''
        script = script.replace("__OUT__", escaped)
        rc, _stdout, stderr = assistant.ps(script, timeout=30)
        if rc != 0 or not os.path.isfile(path) or os.path.getsize(path) == 0:
            try:
                os.remove(path)
            except OSError:
                pass
            raise RuntimeError(stderr or "Windows did not return a screenshot")

    def _capture_after_minimize(self, active_window):
        """Minimize our own UI so the foreground screenshot is the user's other app."""
        if os.name != "nt":
            self.say("Снимок экрана поддерживается только в Windows.", "sys")
            return
        self.root.iconify()
        self.root.after(900, lambda: self._finish_capture(active_window))

    def _finish_capture(self, active_window):
        fd, path = tempfile.mkstemp(prefix="assistant_window_" if active_window else "assistant_screen_", suffix=".png")
        os.close(fd)
        try:
            self._powershell_capture(path, active_window=active_window)
            self.screen_attachments.add(path)
            self.add_files([path])
            self.agent_var.set(False)  # Image analysis is read-only; never route it to PC-action tools.
            if active_window and self.pending_chat_contact:
                prompt = (
                    f"Прочитай снимок активного окна. Я попросил проверить чат «{self.pending_chat_contact}». "
                    "Сначала назови заголовок, который действительно виден. Если это не тот чат или заголовок неразборчив, остановись и скажи об этом. "
                    "Иначе кратко перескажи только видимые последние сообщения и предложи черновик ответа. Ничего не отправляй."
                )
            elif active_window:
                prompt = "Прочитай снимок активного окна и кратко опиши видимый текст. Если это переписка, предложи черновик ответа, ничего не отправляя."
            else:
                prompt = "Опиши, что видно на снимке экрана. Если открыт чат, читай только видимые сообщения и предложи ответ как черновик, не отправляй его."
            self._insert_prompt(prompt)
            self.say("Снимок прикреплён. Он будет передан выбранной локальной vision-модели после отправки запроса.", "sys")
        except Exception as exc:
            try:
                os.remove(path)
            except OSError:
                pass
            self.say(f"Не удалось сделать снимок: {exc}", "sys")
        finally:
            self.root.deiconify()
            self.root.lift()
            self.entry.focus_set()

    def capture_screen(self):
        self._capture_after_minimize(active_window=False)

    def capture_active_window(self):
        self._capture_after_minimize(active_window=True)

    def send(self, _event=None):
        # Screen images must go through read-only chat, never agent actions.
        if self.screen_attachments.intersection(self.attachments):
            self.agent_var.set(False)
        return super().send(_event)

    def clear_attach(self):
        paths = set(self.attachments).intersection(self.screen_attachments)
        super().clear_attach()
        for path in paths:
            self.screen_attachments.discard(path)
            try:
                os.remove(path)
            except OSError:
                pass

    def _new_chat(self):
        if self.attachments:
            self.clear_attach()
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
