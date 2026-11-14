import ctypes, difflib, json, os, queue, random, re, shutil, subprocess, threading, time, urllib.parse, urllib.request, webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import base64, html, zipfile
import urllib.error
import csv, platform, sys, tempfile
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD   # необязательно: перетаскивание файлов (pip install tkinterdnd2)
except Exception:
    DND_FILES = TkinterDnD = None

MODEL = ""        # пусто = выбрать автоматически (первая модель gemma из Ollama). Можно вписать точное имя из ollama list
CODE_MODEL = ""   # пусто = та же модель
API = "http://127.0.0.1:11434"
OLLAMA_EXE = r"D:\AI\Ollama\ollama.exe"
MODELS_DIR = r"D:\AI\models"
WALL_DIR = r"D:\AI\wallpapers"   # картинки для обоев
CODE_DIR = r"D:\AI\projects"     # сюда сохраняется написанный код
HIST_FILE = r"D:\AI\history.json"
ALLOWED_EXT = (".py", ".js", ".html", ".css", ".txt", ".json", ".md", ".bat", ".cpp", ".c", ".cs", ".java")

HOME = os.path.expanduser("~")
TRASH_DIR = r"D:\AI\trash"     # сюда «удалённые» файлы (можно достать обратно)
# Папки, с которыми разрешено работать. Больше никуда программа не заглядывает.
FOLDERS = {"projects": CODE_DIR, "wallpapers": WALL_DIR, "downloads": os.path.join(HOME, "Downloads"),
           "desktop": os.path.join(HOME, "Desktop"), "documents": os.path.join(HOME, "Documents")}
FOLDER_WORDS = {"проект": "projects", "обои": "wallpapers", "обоями": "wallpapers", "обоев": "wallpapers",
                "загрузк": "downloads", "рабоч": "desktop", "документ": "documents"}
TEXT_EXT = (".py", ".js", ".html", ".css", ".txt", ".json", ".md", ".bat", ".cpp", ".c", ".cs", ".java")
CHAT_LOG = r"D:\AI\chat_log.txt"   # сюда пишется всё, что видно в окне, без обрезки
MAX_HISTORY = 1000                 # сколько сообщений хранить в history.json (раньше было 20)
FULL = True                        # доступ ко всему ПК (галочка «Весь ПК»)
EXEC_EXT = (".exe", ".bat", ".cmd", ".ps1", ".msi", ".vbs", ".py", ".jar", ".lnk", ".scr", ".com")   # открытие = запуск, спрашиваем
SKIP_DIRS = {"windows", "program files", "program files (x86)", "programdata", "system volume information",
             "appdata", "$recycle.bin", "node_modules", ".git", "__pycache__", "recovery", "msocache"}
EXT_FIX = {"тхт": "txt", "пдф": "pdf", "пнг": "png", "джпг": "jpg", "жпг": "jpg", "докс": "docx", "пай": "py"}
PROCS = {"notepad": "notepad.exe", "блокнот": "notepad.exe", "discord": "Discord.exe", "дискорд": "Discord.exe",
         "telegram": "Telegram.exe", "телеграм": "Telegram.exe", "steam": "steam.exe", "стим": "steam.exe",
         "chrome": "chrome.exe", "edge": "msedge.exe", "yandex": "browser.exe", "яндекс": "browser.exe",
         "vscode": "Code.exe", "вскод": "Code.exe", "вс код": "Code.exe", "vs code": "Code.exe",
         "paint": "mspaint.exe", "taskmgr": "Taskmgr.exe", "диспетчер задач": "Taskmgr.exe",
         "calc": "CalculatorApp.exe", "калькулятор": "CalculatorApp.exe"}
READ_EXT = (".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv", ".log", ".bat", ".cpp", ".c", ".cs", ".java",
            ".xml", ".yml", ".yaml", ".ini", ".cfg", ".tsv", ".sql")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")

LEVELS = ["Flash", "Средний", "Высокий", "Максимум"]   # режимы: чем выше, тем больше проходов и тем медленнее
AGENT_STEPS = [10, 16, 24, 40]                          # максимум шагов агента в каждом режиме
CODE_TRIES = [1, 2, 3, 4]                              # попытки исправить синтаксис при написании кода
AGENT_ACTIONS = {"list_dir", "read_file", "write_file", "edit_file", "run_command", "find_files", "open_path", "grep", "final"}
PC_ACTIONS = {"open_app", "open_url", "set_wallpaper", "set_wallpaper_url", "save_wallpaper", "volume", "lock",
              "shutdown", "restart", "open_folder", "open_file", "close_app", "say"}
# Команды, которые агенту запрещены совсем (остальные выполняются только после твоего подтверждения)
BLOCKED = [r"\bformat\b", r"\bdiskpart\b", r"\b(rd|rmdir)\b.*\s/s", r"\bdel\b.*\s/[sq]", r"remove-item",
           r"\breg\s+(delete|add|import)", r"\bshutdown\b", r"\btaskkill\b", r"\bnet\s+user", r"\bcurl\b",
           r"\bwget\b", r"invoke-webrequest", r"\bbitsadmin\b", r"\bcertutil\b", r"powershell.*-enc"]

AGENT_SYSTEM = (
    "You are a coding agent working inside a project folder on the user's Windows PC. "
    "You act by emitting exactly ONE action per reply, in this exact format and nothing else:\n"
    "ACTION: list_dir\nPATH: <relative folder, . for the root>\n\n"
    "ACTION: read_file\nPATH: <relative file>\n\n"
    "ACTION: write_file\nPATH: <relative file>\nCONTENT:\n<<<\n<full file content>\n>>>\n\n"
    "ACTION: edit_file\nPATH: <relative file>\nOLD:\n<<<\n<exact existing text, must occur once>\n>>>\nNEW:\n<<<\n<replacement>\n>>>\n\n"
    "ACTION: find_files\nPATH: <file name or part of it, searched on the PC>\n\n"
    "ACTION: open_path\nPATH: <file or folder to open with its default program>\n\n"
    "ACTION: run_command\nCOMMAND: <one Windows cmd command>\n\n"
    "ACTION: final\nMESSAGE: <short summary for the user, in Russian>\n\n"
    "Rules: paths are relative to the project folder; read a file before editing it; prefer edit_file for small changes; "
    "after writing code, run or check it when possible; never touch anything outside the project; "
    "when the task is done or you cannot continue, use final. If the user only asks a question, answer it with final."
)
AGENT_RULES = (
    "Work like a careful senior developer. Rules: understand the task first; if it is unclear or you lack information, ask the user "
    "a short question instead of acting; never invent file names, never write placeholder code such as Hello World, and never create "
    "or change files unless the user asked for it. Explore with list_dir, grep and read_file before editing; read a file before "
    "changing it; prefer edit_file (small exact changes) over write_file; after changes run or check the code when possible and fix "
    "the errors you see; paths are relative to the project folder. When done, reply with a short summary in Russian."
)
AGENT_SYSTEM = AGENT_SYSTEM.replace("ACTION: find_files", "ACTION: grep\nPATH: <regex searched inside project files>\n\nACTION: find_files", 1) + " " + AGENT_RULES

LOCAL = os.environ.get("LOCALAPPDATA", "")
ROAM = os.environ.get("APPDATA", "")

# Разрешённые программы: имя -> команда. Добавляй свои строки сюда.
DISCORD = f'"{LOCAL}\\Discord\\Update.exe" --processStart Discord.exe'
TELEGRAM = f'"{ROAM}\\Telegram Desktop\\Telegram.exe"'
YANDEX = f'"{LOCAL}\\Yandex\\YandexBrowser\\Application\\browser.exe"'
APPS = {
    "notepad": "notepad", "блокнот": "notepad",
    "calc": "calc", "калькулятор": "calc",
    "paint": "mspaint",
    "taskmgr": "taskmgr", "диспетчер задач": "taskmgr",
    "explorer": "explorer", "проводник": "explorer",
    "settings": "ms-settings:", "параметры": "ms-settings:",
    "steam": "steam://open/main", "стим": "steam://open/main",
    "discord": DISCORD, "дискорд": DISCORD,
    "telegram": TELEGRAM, "телеграм": TELEGRAM,
    "chrome": "chrome", "edge": "msedge",
    "yandex": YANDEX, "яндекс": YANDEX,
    "vscode": "code", "вскод": "code", "вс код": "code", "vs code": "code",
}
SITES = {"youtube": "https://www.youtube.com", "ютуб": "https://www.youtube.com",
         "google": "https://www.google.com", "гугл": "https://www.google.com",
         "github": "https://github.com", "гитхаб": "https://github.com"}

VALID = {"chat", "open_app", "open_url", "write_code", "set_wallpaper", "set_wallpaper_url", "save_wallpaper", "list_files", "open_folder", "read_file", "delete_file", "volume", "lock", "shutdown", "restart", "type_text", "telegram_message", "open_file", "close_app"}
QUESTION_WORDS = ("как", "что", "почему", "зачем", "где", "какой", "какая", "какие", "сколько", "расскажи", "объясни", "когда", "кто")
# Модель-планировщик вызывается только если в сообщении есть такие слова
GATE = ("напиши", "написать", "создай", "сделай", "код", "программ", "скрипт", "игр", "приложен", "открой", "запусти",
        "включи", "найди", "закрой", "отправь", "сообщени", "телеграм", "telegram", "напечатай", "добавь", "измени", "исправь", "переделай", "файл", "обои", "громк", "звук", "закрой")
WRITE_WORDS = ("напиши", "написать", "создай", "сделай", "код", "программ", "скрипт", "игр", "приложен", "добавь",
               "измени", "исправь", "переделай", "файл", "змейк", "бот")

ROUTER = (
    "You are the planner of a Windows PC assistant. Answer with ONE JSON object: "
    '{"steps":[{"action":"...","arg":"..."}]}. '
    "Actions: chat (arg empty); "
    "open_app (arg is exactly one of: " + ", ".join(APPS) + "); "
    "open_url (arg is a full https URL); "
    "write_code (only for programs and code, never for messages to people; arg is 'filename.ext | what the program must do'; "
    "creates the file and opens it in VS Code; "
    "to change a file written earlier use the same filename); "
    "list_files and open_folder (arg is a folder key); read_file and delete_file (arg is 'folder key | filename'); "
    "folder keys: projects, wallpapers, downloads, desktop, documents; save_wallpaper (saves the current wallpaper); "
    "open_file (arg is 'file name or path | program'; the program is optional and is one of the open_app names; opens a file or "
    "folder found anywhere on the PC); close_app (arg is one of the open_app names); "
    "type_text (arg is the exact text to type into the program opened by the previous open_app step; only right after open_app); "
    "telegram_message (arg is 'recipient | text', recipient is @username or a contact name, leave a part empty if the user did not say it; use AUTO as the text if the user lets you write it yourself; "
    "it opens Telegram itself, never add open_app for it); "
    "set_wallpaper; volume (arg 'up N', 'down N' or 'mute'); lock; shutdown; restart. "
    "Several steps are allowed, in order. Use chat when unsure. Never invent actions or programs.\n"
    'User: открой вскод и напиши змейку -> {"steps":[{"action":"write_code","arg":"snake.py | Snake game in Python with tkinter"}]}\n'
    'User: открой мне окно с игрой змейка -> {"steps":[{"action":"write_code","arg":"snake.py | Snake game in Python with tkinter"}]}\n'
    'User: открой блокнот с именем ошибки.txt -> {"steps":[{"action":"open_file","arg":"ошибки.txt | notepad"}]}\n'
    'User: открой блокнот и напиши привет -> {"steps":[{"action":"open_app","arg":"notepad"},{"action":"type_text","arg":"привет"}]}\n'
    'User: напиши Васе в телеграм привет -> {"steps":[{"action":"telegram_message","arg":"Вася | привет"}]}\n'
    'User: напиши контакту Даня с юзом @Mr_Dablocer сам что думаешь -> {"steps":[{"action":"telegram_message","arg":"@Mr_Dablocer | AUTO"}]}\n'
    'User: открой телеграм и напиши сообщение -> {"steps":[{"action":"telegram_message","arg":" | "}]}\n'
    'User: что такое процессор? -> {"steps":[{"action":"chat","arg":""}]}'
)
CHAT_SYSTEM = ("You are a helpful assistant running locally on the user's PC. Always answer in Russian and never in Chinese "
               "(use another language only if the user writes in it). Be clear and not too long. You only know what is written in this conversation. If the user refers to "
               "something you cannot see here, say you don't remember instead of inventing. If you are unsure, say so.")
CODE_SYSTEM = ("You are an expert programmer. Reply with the complete code of ONE file inside a single fenced code block "
               "and nothing else. Use only the Python standard library (tkinter for windows and games) unless the task "
               "says otherwise. The code must run as is. Short comments in Russian are fine.")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")   # китайские/японские символы
OPTS = {"num_ctx": 12288}   # одинаковый контекст везде, чтобы модель не перезагружалась


def server_up():
    try:
        urllib.request.urlopen(API, timeout=2)
        return True
    except Exception:
        return False


def ensure_server():
    if server_up():
        return True
    env = dict(os.environ, OLLAMA_MODELS=MODELS_DIR)
    try:
        subprocess.Popen([OLLAMA_EXE, "serve"], env=env, creationflags=0x08000000)
    except Exception:
        return False
    for _ in range(20):
        time.sleep(1)
        if server_up():
            return True
    return False


VISION = False   # понимает ли модель картинки
THINKS = None   # есть ли у модели встроенное «размышление» (определяется автоматически)


def pick_model():
    """Находит в Ollama установленную модель gemma (лучше 12b) и использует её везде."""
    global MODEL, CODE_MODEL, THINKS, VISION
    if not MODEL:
        try:
            with urllib.request.urlopen(API + "/api/tags", timeout=5) as r:
                names = [m["name"] for m in json.loads(r.read()).get("models", [])]
        except Exception:
            return False
        pool = [n for n in names if n.lower().startswith("gemma")] or names
        if not pool:
            return False
        MODEL = sorted(pool, key=lambda n: "12b" not in n.lower())[0]
    CODE_MODEL = CODE_MODEL or MODEL
    if THINKS is None:
        try:
            with post("/api/show", {"model": MODEL}, 15) as r:
                caps = json.loads(r.read()).get("capabilities", [])
                THINKS, VISION = "thinking" in caps, "vision" in caps
        except Exception:
            THINKS = False
    return True


def post(path, payload, timeout=600):
    req = urllib.request.Request(API + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def local_plan(text):
    """Простые команды разбираем без модели: быстро и без ошибок."""
    t = text.lower().strip()
    url = re.search(r"https?://\S+", text)
    if url and "обои" in t:
        return [{"action": "set_wallpaper_url", "arg": url.group(0)}]
    first = t.split()[0] if t.split() else ""
    tg = re.search(r"(?:напиши|отправь|скинь|пошли)\s+(?:контакту|юзеру|пользователю)\s+(@?\w+)[\s,:\-]+(?:в\s+(?:телеграмм?|тг)\s+)?(.+)$", text, re.I | re.S)
    if tg and not re.search(r"@|\bсам\b|придумай", t):
        return [{"action": "telegram_message", "arg": f"{tg.group(1)} | {tg.group(2).strip()}"}]
    is_q = "?" in t or first in QUESTION_WORDS
    fm = re.search(r"[\w\-]+\.(?:py|js|html|css|txt|json|md|bat|cpp|c|cs|java|jpg|jpeg|png|bmp|zip|pdf|docx|xlsx|csv|log|тхт|пдф|пнг|джпг)\b", t)
    fkey = next((v for k, v in FOLDER_WORDS.items() if k in t), None)
    if re.search(r"сохрани.*обои|обои.*сохрани", t) and not url:
        return [{"action": "save_wallpaper", "arg": ""}]
    if (not is_q or first in ("объясни", "разбери")) and fm and re.search(r"прочитай|посмотри|разбери|объясни|что в файле|покажи код", t):
        return [{"action": "read_file", "arg": f"{fkey or 'projects'} | {fm.group(0)}"}]
    if fkey and re.match(r"что (в |лежит)", t):
        return [{"action": "list_files", "arg": fkey}]
    dm = re.search(r"диск[еау]?\s+([a-z])\b", t)
    if dm and re.search(r"файл|что на|что лежит|покажи|список", t):
        return [{"action": "list_files", "arg": dm.group(1).upper() + ":\\"}]
    if not is_q:
        if fm and re.search(r"удали|убери", t):
            return [{"action": "delete_file", "arg": f"{fkey or 'projects'} | {fix_ext(fm.group(0))}"}]
        if re.search(r"закро\w+\s+все", t):
            steps = [{"action": "say", "arg": "Закрыть все приложения сразу я не буду: так можно потерять несохранённую работу. "
                                              "Назови конкретные программы, например: «закрой дискорд и телеграм»."}]
            tail = re.search(r"откро\w*\s+(.+)$", t)
            if tail:
                keys = apps_in_text(tail.group(1))
                if keys:
                    steps.append({"action": "open_app", "arg": keys[0]})
            return steps
        if re.search(r"закро\w+", t) and apps_in_text(t):
            return [{"action": "close_app", "arg": k} for k in apps_in_text(t)]
        nm = (re.search(r"(?:с именем|под именем|с названием|под названием|по имени)\s+(.+)$", t)
              or re.search(r"(?:откро\w*|найди|запусти)\s+(?:файл|документ)\s+(.+)$", t))
        raw = nm.group(1).strip(" .") if nm else (fm.group(0) if fm else None)
        if raw and re.search(r"откро|запусти|найди", t) and len(t.split()) <= 8 \
                and not re.search(r"\sи\s+(напиши|добавь|измени|исправь|удали|создай)", t):
            prog = next((k for k in sorted(APPS, key=len, reverse=True) if k in t.replace(raw, "")), "")
            return [{"action": "open_file", "arg": f"{fix_ext(raw)} | {prog}"}]
        if fkey and re.search(r"откро", t) and ("папк" in t or "загрузк" in t or "рабоч" in t):
            return [{"action": "open_folder", "arg": fkey}]
        if fkey and re.search(r"файл|что в |что лежит|список|покажи", t):
            return [{"action": "list_files", "arg": fkey}]
    if not t or is_q:
        return None
    if re.search(r"без звука|выключи звук|отключи звук|заглуши|mute", t):
        return [{"action": "volume", "arg": "mute"}]
    if re.search(r"громкост|звук|тише|громче", t):
        m = re.search(r"\d+", t)
        n = m.group() if m else "5"
        if re.search(r"тише|меньше|убав|уменьш|снизь|ниже", t):
            return [{"action": "volume", "arg": f"down {n}"}]
        if re.search(r"громче|больше|прибав|увелич|повысь|выше", t):
            return [{"action": "volume", "arg": f"up {n}"}]
    if "обои" in t:
        return [{"action": "set_wallpaper", "arg": "random"}]
    if re.search(r"заблокируй|блокировк", t):
        return [{"action": "lock", "arg": ""}]
    if re.search(r"выключи (компьютер|пк|комп)|заверши работу", t):
        return [{"action": "shutdown", "arg": ""}]
    if "перезагрузи" in t:
        return [{"action": "restart", "arg": ""}]
    m = re.search(r"(?:загугли|найди в интернете|поищи в интернете|найди в гугле)\s+(.+)", t)
    if m:
        return [{"action": "open_url", "arg": "https://www.google.com/search?q=" + urllib.parse.quote(m.group(1))}]
    if re.search(r"откро|запусти|включи", t) and len(t.split()) <= 4:   # длинные просьбы разбирает планировщик или агент
        for key in sorted(APPS, key=len, reverse=True):
            if key in t:
                return [{"action": "open_app", "arg": key}]
        for key, url in SITES.items():
            if key in t:
                return [{"action": "open_url", "arg": url}]
    return None


def route(history, last_name):
    """Модель составляет план действий (JSON). Вызывается только для неочевидных запросов."""
    system = ROUTER + (f"\nLast file you wrote: {last_name}" if last_name else "")
    payload = {"model": MODEL, "messages": [{"role": "system", "content": system}] + history[-6:],
               "stream": False, "format": "json", "keep_alive": "30m",
               "options": dict(OPTS, temperature=0.1, num_predict=150)}
    if THINKS:
        payload["think"] = False
    with post("/api/chat", payload) as r:
        raw = json.loads(r.read())["message"]["content"]
    try:
        return [s for s in json.loads(raw).get("steps", []) if isinstance(s, dict)]
    except Exception:
        return []


def stream(model, messages, stop, temperature=0.4, num_predict=None, think=None, on_think=None):
    """Генератор кусков текста. Останавливается по событию stop.
    think=True/False включает или выключает встроенное размышление (только если модель его умеет)."""
    opts = dict(OPTS, temperature=temperature)
    if num_predict:
        opts["num_predict"] = num_predict
    payload = {"model": model, "messages": messages, "stream": True, "keep_alive": "30m", "options": opts}
    if think is not None and THINKS:
        payload["think"] = think
    with post("/api/chat", payload) as r:
        for line in r:
            if stop.is_set():
                break
            if not line.strip():
                continue
            d = json.loads(line)
            msg = d.get("message", {})
            if msg.get("thinking") and on_think:
                on_think(msg["thinking"])
            piece = msg.get("content", "")
            if piece:
                yield piece
            if d.get("done"):
                break


def complete(model, messages, stop, temperature=0.3, num_predict=None, think=None):
    """То же, что stream, но возвращает весь текст сразу (для скрытых проходов «подумать»)."""
    return "".join(stream(model, messages, stop, temperature, num_predict, think))


def with_note(msgs, note):
    out = list(msgs)
    out[-1] = dict(out[-1], content=out[-1]["content"] + "\n\n" + note)
    return out


def is_protected(p):
    """Системные папки Windows: их менять нельзя."""
    pl = os.path.normcase(os.path.abspath(p))
    for var, default in (("SystemRoot", r"C:\Windows"), ("ProgramFiles", r"C:\Program Files"),
                         ("ProgramFiles(x86)", r"C:\Program Files (x86)"), ("ProgramData", r"C:\ProgramData")):
        r = os.path.normcase(os.path.abspath(os.environ.get(var, default)))
        if pl == r or pl.startswith(r + os.sep):
            return True
    return False


def inside(ws, p):
    a, b = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(ws))
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:
        return False


def safe_path(ws, rel, full=False):
    """Путь для агента. Без «Весь ПК» выход за папку проекта запрещён."""
    rel = rel.strip().strip('"').strip("'")
    p = os.path.abspath(os.path.join(ws, rel))
    if not full and not inside(ws, p):
        raise ValueError("путь вне папки проекта")
    return p


def fix_ext(name):
    """«ошибки.тхт» -> «ошибки.txt»."""
    return re.sub(r"\.(%s)\b" % "|".join(EXT_FIX), lambda m: "." + EXT_FIX[m.group(1).lower()], name, flags=re.I)


def apps_in_text(t):
    seen, out = set(), []
    for key in sorted(APPS, key=len, reverse=True):
        if key in t:
            proc = PROCS.get(key, key)
            if proc not in seen:
                seen.add(proc)
                out.append(key)
    return out


def search_roots():
    roots = [os.path.join(HOME, d) for d in ("Desktop", "Downloads", "Documents", "Pictures", "Videos", "Music")] + [HOME]
    try:
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            d = f"{chr(65 + i)}:\\"
            if mask & (1 << i) and ctypes.windll.kernel32.GetDriveTypeW(d) == 3:
                roots.append(d)
    except Exception:
        pass
    return [r for r in dict.fromkeys(roots) if os.path.isdir(r)]


def find_files(query, limit=10, timeout=10, roots=None, max_depth=7):
    """Ищет файлы по имени на дисках. Сначала папки пользователя, потом всё остальное."""
    q = fix_ext(query.strip().strip("\"'")).lower()
    if not q:
        return []
    has_ext = bool(os.path.splitext(q)[1])
    deadline, hits, seen = time.time() + timeout, [], set()
    all_roots = roots or search_roots()
    for n, root in enumerate(all_roots):
        base = root.rstrip("\\/").count(os.sep)
        for dp, dns, fns in os.walk(root):
            if time.time() > deadline:
                break
            dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS and not d.startswith("$")] if dp.count(os.sep) - base < max_depth else []
            for fn in fns:
                low = fn.lower()
                key = low if has_ext else os.path.splitext(low)[0]
                score = 0 if key == q else (1 if q in key else None)
                path = os.path.join(dp, fn)
                if score is None or path.lower() in seen:
                    continue
                seen.add(path.lower())
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    mtime = 0
                hits.append((score, -mtime, path))
        if time.time() > deadline or (roots is None and n >= 5 and any(h[0] == 0 for h in hits)):
            break   # точное совпадение уже есть в папках пользователя: дальше не ищем
    hits.sort()
    return [h[2] for h in hits[:limit]]


def looks_text(path):
    try:
        with open(path, "rb") as f:
            return b"\0" not in f.read(2048)
    except OSError:
        return False


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    return html.unescape(re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n")))


def load_attachments(paths, vision):
    """Читает прикреплённые файлы. Возвращает (текст для модели, картинки в base64, заметки пользователю)."""
    blob, images, notes = [], [], []
    for p in paths:
        name, ext = os.path.basename(p), os.path.splitext(p)[1].lower()
        try:
            if ext in IMG_EXT:
                if not vision:
                    notes.append(f"{name}: эта модель не понимает картинки, выбери другую модель.")
                elif os.path.getsize(p) > 8_000_000:
                    notes.append(f"{name}: картинка больше 8 МБ, не прикрепил.")
                else:
                    with open(p, "rb") as f:
                        images.append(base64.b64encode(f.read()).decode())
                    notes.append(f"{name}: картинка передана модели.")
            elif ext == ".docx":
                blob.append(f"File {name}:\n```\n{read_docx(p)[:6000]}\n```")
            elif ext in READ_EXT or looks_text(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    blob.append(f"File {name}:\n```\n{f.read(6000)}\n```")
            else:
                blob.append(f"Attached file (binary, its content cannot be read here): {p}")
                notes.append(f"{name}: формат не читается, модели передан только путь.")
        except Exception as e:
            notes.append(f"{name}: не удалось прочитать ({e}).")
    return "\n\n".join(blob), images, notes


def parse_action(text):
    m = re.search(r"ACTION:\s*(\w+)", text)
    if not m:
        return None
    path = re.search(r"^PATH:\s*(.+)$", text, re.M)
    cmd = re.search(r"^COMMAND:\s*(.+)$", text, re.M)
    msg = re.search(r"^MESSAGE:\s*(.*)", text, re.M | re.S)
    return {"action": m.group(1).lower(),
            "path": path.group(1).strip() if path else "",
            "command": cmd.group(1).strip() if cmd else "",
            "message": msg.group(1).strip().rstrip("`\n ") if msg else "",
            "blocks": re.findall(r"<<<[ \t]*\n(.*?)\n>>>", text, re.S)}


def run_cmd(cmd, cwd):
    low = cmd.lower()
    if any(re.search(pat, low) for pat in BLOCKED):
        return "BLOCKED: this command is not allowed."
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    note = b""
    try:
        out, _ = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        out, _ = proc.communicate()
        note = b"\n[stopped after 60 seconds]"
    out += note
    try:
        text = out.decode("oem", errors="replace")
    except LookupError:
        text = out.decode("utf-8", errors="replace")
    return f"exit code {proc.returncode}\n{text[-3000:]}"


UNDO_DIR = r"D:\AI\undo"
UNDO = []   # (путь, копия до изменения или None, если файл создан агентом)


def backup(p):
    try:
        os.makedirs(UNDO_DIR, exist_ok=True)
        if os.path.isfile(p):
            b = os.path.join(UNDO_DIR, f"{int(time.time() * 1000)}_{os.path.basename(p)}")
            shutil.copy2(p, b)
            UNDO.append((p, b))
        else:
            UNDO.append((p, None))
    except Exception:
        pass


def undo_last():
    if not UNDO:
        return "Отменять нечего."
    p, b = UNDO.pop()
    try:
        if b:
            shutil.copy2(b, p)
            return f"Возвращено прежнее содержимое: {p}"
        if os.path.isfile(p):
            os.makedirs(TRASH_DIR, exist_ok=True)
            shutil.move(p, os.path.join(TRASH_DIR, f"{int(time.time())}_{os.path.basename(p)}"))
        return f"Созданный файл убран в корзину ассистента: {p}"
    except Exception as e:
        return f"Не удалось отменить: {e}"


def _int(v, d):
    try:
        return int(v)
    except Exception:
        return d


def grep_files(ws, pattern, path, full):
    try:
        rx = re.compile(pattern, re.I)
    except re.error as e:
        return f"ERROR: bad regex: {e}"
    root = safe_path(ws, path or ".", full)
    files = [root] if os.path.isfile(root) else []
    if os.path.isdir(root):
        for d, dirs, fs in os.walk(root):
            dirs[:] = [x for x in dirs if x.lower() not in SKIP_DIRS]
            files += [os.path.join(d, f) for f in fs if f.lower().endswith(READ_EXT)]
            if len(files) > 3000:
                break
    base = root if os.path.isdir(root) else os.path.dirname(root)
    hits = []
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if rx.search(line):
                        hits.append(f"{os.path.relpath(f, base)}:{n}: {line.strip()[:160]}")
                        if len(hits) >= 40:
                            return "\n".join(hits) + "\n...[more matches, narrow the search]"
        except Exception:
            pass
    return "\n".join(hits) or "(no matches)"


def _tool(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": {k: ({"type": "array", "items": {"type": "string"}, "description": v[1]} if v[0] == "array"
                                          else {"type": v[0], "description": v[1]}) for k, v in props.items()}, "required": req}}}


TOOLS = [
    _tool("list_dir", "List files and folders in a folder.", {"path": ("string", "folder, . for the project root")}, ["path"]),
    _tool("read_file", "Read a text file (lines are numbered). Use start/end to read part of a big file.",
          {"path": ("string", "file path"), "start": ("integer", "first line"), "end": ("integer", "last line")}, ["path"]),
    _tool("grep", "Search text (regex) inside project files. Returns file:line: text.",
          {"pattern": ("string", "regex"), "path": ("string", "folder or file, default .")}, ["pattern"]),
    _tool("find_files", "Find files by name.", {"name": ("string", "file name or part of it")}, ["name"]),
    _tool("write_file", "Create a file or overwrite it completely.",
          {"path": ("string", "file path"), "content": ("string", "full file content")}, ["path", "content"]),
    _tool("edit_file", "Replace exact text in a file. old must occur exactly once. Do not include line numbers.",
          {"path": ("string", "file path"), "old": ("string", "exact existing text"), "new": ("string", "replacement")}, ["path", "old", "new"]),
    _tool("run_command", "Run one Windows cmd command in the project folder (the user confirms it).",
          {"command": ("string", "the command")}, ["command"]),
    _tool("open_path", "Open a file or folder with its default program.", {"path": ("string", "path")}, ["path"]),
]
TOOLS += [
    _tool("make_dir", "Create a folder.", {"path": ("string", "folder")}, ["path"]),
    _tool("move_file", "Move or rename a file or folder.", {"src": ("string", "from"), "dst": ("string", "to (file or folder)")}, ["src", "dst"]),
    _tool("copy_file", "Copy a file or folder.", {"src": ("string", "from"), "dst": ("string", "to")}, ["src", "dst"]),
    _tool("delete_file", "Move a file or folder to the assistant trash (recoverable).", {"path": ("string", "path")}, ["path"]),
    _tool("file_info", "Size, dates and type of a path.", {"path": ("string", "path")}, ["path"]),
    _tool("zip_files", "Zip a file or folder.", {"src": ("string", "what to zip"), "dst": ("string", "zip file, optional")}, ["src"]),
    _tool("unzip", "Extract a zip file.", {"path": ("string", "zip file"), "dst": ("string", "folder, optional")}, ["path"]),
    _tool("run_python", "Run a Python script (the user confirms).", {"code": ("string", "full script")}, ["code"]),
    _tool("web_search", "Search the web: titles, links, snippets.", {"query": ("string", "search query")}, ["query"]),
    _tool("web_fetch", "Download a web page as text.", {"url": ("string", "https link")}, ["url"]),
    _tool("download_file", "Download a file from a link (the user confirms).", {"url": ("string", "https link"), "path": ("string", "file or folder, default Downloads")}, ["url"]),
    _tool("open_app", "Open a program by name (telegram, discord, notepad, ...).", {"name": ("string", "program")}, ["name"]),
    _tool("open_url", "Open a link in the browser.", {"url": ("string", "https link")}, ["url"]),
    _tool("close_app", "Close a program by name.", {"name": ("string", "program")}, ["name"]),
    _tool("volume", "Change volume: 'up N', 'down N' or 'mute'.", {"arg": ("string", "e.g. up 5")}, ["arg"]),
    _tool("set_wallpaper", "Change the wallpaper (random or by part of the file name).", {"name": ("string", "optional")}, []),
    _tool("power_action", "lock, shutdown or restart the PC (the user confirms).", {"arg": ("string", "lock, shutdown or restart")}, ["arg"]),
    _tool("clipboard_get", "Read the clipboard text.", {}, []),
    _tool("clipboard_set", "Put text into the clipboard.", {"text": ("string", "text")}, ["text"]),
    _tool("screenshot", "Save a screenshot of the screen as PNG.", {"path": ("string", "png file, optional")}, []),
    _tool("list_processes", "Running programs sorted by memory.", {}, []),
    _tool("system_info", "OS, RAM and disks.", {}, []),
    _tool("telegram_message", "Send a Telegram message (the user confirms).", {"recipient": ("string", "@username or contact name"), "text": ("string", "message")}, ["recipient", "text"]),
    _tool("todo", "Write or update the checklist of steps for a long task.", {"items": ("array", "steps; prefix finished ones with [x]")}, ["items"]),
]
TOOL_NAMES = {t["function"]["name"] for t in TOOLS}
VAGUE = re.compile(r"^(заново|ещё раз|еще раз|повтори|продолжай|продолжи|давай|давай ещё|давай еще|ок|окей|да|делай|ну|снова|попробуй снова|попробуй ещё раз|попробуй еще раз)\W*$", re.I)
_CAPS = {}


def model_caps(model):
    if model not in _CAPS:
        try:
            with post("/api/show", {"model": model}, 15) as r:
                _CAPS[model] = json.loads(r.read()).get("capabilities", [])
        except Exception:
            _CAPS[model] = []
    return _CAPS[model]


def chat_tools(model, messages, stop, think=None, on_think=None):
    """Один шаг агента с настоящим вызовом инструментов Ollama. Возвращает (текст, список вызовов)."""
    payload = {"model": model, "messages": messages, "tools": TOOLS, "stream": True, "keep_alive": "30m",
               "options": dict(OPTS, temperature=0.2)}
    if think is not None and THINKS:
        payload["think"] = think
    text, calls = [], []
    with post("/api/chat", payload) as r:
        for line in r:
            if stop.is_set():
                break
            if not line.strip():
                continue
            d = json.loads(line)
            m = d.get("message", {})
            if m.get("thinking") and on_think:
                on_think(m["thinking"])
            if m.get("content"):
                text.append(m["content"])
            calls += m.get("tool_calls") or []
            if d.get("done"):
                break
    return "".join(text), calls


def tool_args(name, args):
    if not isinstance(args, dict):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    g = lambda k: str(args.get(k) if args.get(k) is not None else "")
    a = {"action": name, "path": g("path") or g("name"), "command": g("command"), "blocks": [], "numbered": True,
         "pattern": g("pattern"), "start": args.get("start"), "end": args.get("end"), "args": args}
    if name == "write_file" and args.get("content") is not None:
        a["blocks"] = [g("content")]
    if name == "edit_file" and args.get("old"):
        a["blocks"] = [g("old"), g("new")]
    return a


def _trash(p):
    os.makedirs(TRASH_DIR, exist_ok=True)
    d = os.path.join(TRASH_DIR, f"{int(time.time())}_{os.path.basename(p.rstrip(chr(92) + '/'))}")
    shutil.move(p, d)
    return d


def _http_get(url, limit=500_000, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit), (r.headers.get_content_charset() or "utf-8")


def html_to_text(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h\d>|</tr>", "\n", h)
    h = html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))
    h = re.sub(r"[ \t\r\f\v]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def web_search(q):
    data, cs = _http_get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
    h = data.decode(cs, errors="replace")
    links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S)
    snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', h, re.S)
    out = []
    for i, (href, title) in enumerate(links[:8]):
        m = re.search(r"uddg=([^&]+)", href)
        url = urllib.parse.unquote(m.group(1)) if m else href
        out.append(f"{i + 1}. {html_to_text(title)}\n   {url}\n   {html_to_text(snips[i]) if i < len(snips) else ''}")
    return "\n".join(out) or "(no results; the search engine may be blocked, try web_fetch on a known site)"


def ps(script, inp=None, timeout=30):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], input=inp, capture_output=True,
                       timeout=timeout, creationflags=0x08000000)
    return r.returncode, r.stdout.decode("utf-8", errors="replace").strip(), r.stderr.decode("utf-8", errors="replace").strip()


def list_processes():
    r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, creationflags=0x08000000)
    try:
        t = r.stdout.decode("oem", errors="replace")
    except LookupError:
        t = r.stdout.decode("utf-8", errors="replace")
    agg = {}
    for row in csv.reader(t.splitlines()):
        if len(row) >= 5:
            c, m = agg.get(row[0], (0, 0))
            agg[row[0]] = (c + 1, m + int(re.sub(r"\D", "", row[4]) or 0))
    top = sorted(agg.items(), key=lambda kv: -kv[1][1])[:40]
    return "\n".join(f"{n} x{c}  {m // 1024} MB" for n, (c, m) in top) or "(no data)"


def system_info():
    lines = [platform.platform(), f"CPU threads: {os.cpu_count()}", f"User: {os.environ.get('USERNAME', '')}"]
    try:
        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                        ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong),
                        ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
        m = MS()
        m.l = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        lines.append(f"RAM: {m.ap / 2**30:.1f} GB free of {m.tp / 2**30:.1f} GB")
    except Exception:
        pass
    for L in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        try:
            u = shutil.disk_usage(L + ":\\")
            lines.append(f"Disk {L}: {u.free / 2**30:.0f} GB free of {u.total / 2**30:.0f} GB")
        except Exception:
            pass
    return "\n".join(lines)


def known_folders():
    out = dict(FOLDERS)
    try:
        buf = ctypes.create_unicode_buffer(520)
        for key, csidl in (("desktop", 0x10), ("documents", 5)):
            if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0 and buf.value:
                out[key] = buf.value
    except Exception:
        pass
    return out


def extra_tool(ws, a, confirm, ask, changed, full):
    """Остальные инструменты агента: файлы, архивы, интернет, программы, буфер обмена, экран."""
    act, g = a["action"], a.get("args") or {}
    s = lambda k: str(g.get(k) if g.get(k) is not None else "").strip()
    prot = lambda *ps_: "ERROR: system folder, not allowed" if any(is_protected(x) for x in ps_) else None
    if act == "make_dir":
        p = safe_path(ws, s("path"), full)
        if prot(p):
            return prot(p)
        os.makedirs(p, exist_ok=True)
        return f"OK: folder {p}"
    if act in ("move_file", "copy_file"):
        src, dst = safe_path(ws, s("src"), full), safe_path(ws, s("dst"), full)
        if not os.path.exists(src):
            return "ERROR: source not found"
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src.rstrip("\\/")))
        err = prot(src, dst) if act == "move_file" else prot(dst)
        if err:
            return err
        if os.path.exists(dst):
            return "ERROR: destination already exists; choose another name"
        if (ask or not inside(ws, src) or not inside(ws, dst)) and not confirm(
                f"{'Переместить' if act == 'move_file' else 'Копировать'}:\n{src}\n→ {dst}"):
            return "USER DENIED this action."
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if act == "move_file":
            shutil.move(src, dst)
        elif os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return f"OK: {src} -> {dst}"
    if act == "delete_file":
        p = safe_path(ws, s("path"), full)
        if not os.path.exists(p):
            return "ERROR: not found"
        if prot(p):
            return prot(p)
        if os.path.abspath(p) in (os.path.abspath(ws), os.path.splitdrive(os.path.abspath(p))[0] + "\\"):
            return "ERROR: refusing to delete a project or drive root"
        if not confirm(f"Убрать в корзину ассистента ({TRASH_DIR}):\n{p}?"):
            return "USER DENIED this action."
        return f"OK: moved to {_trash(p)} (recoverable)"
    if act == "file_info":
        p = safe_path(ws, s("path"), full)
        if not os.path.exists(p):
            return "ERROR: not found"
        st = os.stat(p)
        kind = "folder" if os.path.isdir(p) else "file"
        extra_ = f", {len(os.listdir(p))} items" if kind == "folder" else f", {st.st_size} bytes"
        return f"{kind}{extra_}, modified {time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime))}"
    if act == "zip_files":
        src = safe_path(ws, s("src"), full)
        if not os.path.exists(src):
            return "ERROR: source not found"
        dst = safe_path(ws, s("dst") or src.rstrip("\\/") + ".zip", full)
        if prot(dst):
            return prot(dst)
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
            if os.path.isdir(src):
                for d, _, fs in os.walk(src):
                    for f in fs:
                        fp = os.path.join(d, f)
                        z.write(fp, os.path.relpath(fp, os.path.dirname(src)))
            else:
                z.write(src, os.path.basename(src))
        return f"OK: {dst}"
    if act == "unzip":
        src = safe_path(ws, s("path"), full)
        if not zipfile.is_zipfile(src):
            return "ERROR: not a zip file"
        dst = safe_path(ws, s("dst") or os.path.splitext(src)[0], full)
        if prot(dst):
            return prot(dst)
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                if not inside(dst, os.path.join(dst, n)):
                    return "ERROR: unsafe path inside the archive"
            z.extractall(dst)
        return f"OK: extracted to {dst}"
    if act == "run_python":
        code = str(g.get("code") or "")
        if not code.strip():
            return "ERROR: code missing"
        if not confirm(f"Запустить Python-код в папке проекта?\n\n{code[:900]}"):
            return "USER DENIED this action."
        fd, tmp = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            return run_cmd(f'"{sys.executable.replace("pythonw.exe", "python.exe")}" "{tmp}"', ws)
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
    if act == "web_search":
        return web_search(s("query")) if s("query") else "ERROR: query missing"
    if act == "web_fetch":
        url = s("url")
        if not url.startswith(("http://", "https://")):
            return "ERROR: url must start with http(s)"
        data, cs = _http_get(url)
        text = html_to_text(data.decode(cs, errors="replace"))
        return text[:6000] + ("\n...[truncated]" if len(text) > 6000 else "")
    if act == "download_file":
        url = s("url")
        if not url.startswith(("http://", "https://")):
            return "ERROR: url must start with http(s)"
        p = safe_path(ws, s("path") or FOLDERS["downloads"], full)
        if os.path.isdir(p):
            p = os.path.join(p, os.path.basename(urllib.parse.urlparse(url).path) or "download.bin")
        if prot(p):
            return prot(p)
        if os.path.exists(p):
            return "ERROR: file already exists; choose another name"
        if not confirm(f"Скачать файл\n{url}\nв {p}?"):
            return "USER DENIED this action."
        os.makedirs(os.path.dirname(p), exist_ok=True)
        size = 0
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(p, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > 300_000_000:
                    f.close()
                    os.remove(p)
                    return "ERROR: file is larger than 300 MB"
                f.write(chunk)
        return f"OK: saved {p} ({size} bytes)"
    if act in ("open_app", "open_url", "close_app", "volume", "set_wallpaper"):
        ok, msg = run_action(act, s("name") or s("url") or s("arg"), confirm)
        return ("OK: " if ok else "ERROR: ") + msg
    if act == "power_action":
        k = s("arg").lower()
        if k not in ("lock", "shutdown", "restart"):
            return "ERROR: arg must be lock, shutdown or restart"
        ok, msg = run_action(k, "", confirm)
        return ("OK: " if ok else "ERROR: ") + msg
    if act == "clipboard_get":
        rc, out, err = ps("[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw")
        return (out[:4000] or "(clipboard is empty)") if rc == 0 else f"ERROR: {err[:200]}"
    if act == "clipboard_set":
        rc, _, err = ps("[Console]::InputEncoding=[Text.Encoding]::UTF8; $t=[Console]::In.ReadToEnd(); Set-Clipboard -Value $t",
                        inp=str(g.get("text") or "").encode("utf-8"))
        return "OK: copied" if rc == 0 else f"ERROR: {err[:200]}"
    if act == "screenshot":
        p = safe_path(ws, s("path") or f"screenshot_{int(time.strftime('%H%M%S'))}.png", full)
        if prot(p):
            return prot(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        rc, _, err = ps("Add-Type -AssemblyName System.Windows.Forms,System.Drawing; $s=[System.Windows.Forms.SystemInformation]::VirtualScreen; "
                        "$b=New-Object System.Drawing.Bitmap $s.Width,$s.Height; $g=[System.Drawing.Graphics]::FromImage($b); "
                        f"$g.CopyFromScreen($s.Left,$s.Top,0,0,$b.Size); $b.Save('{p.replace(chr(39), chr(39) * 2)}')")
        return f"OK: saved {p}" if rc == 0 and os.path.isfile(p) else f"ERROR: {err[:200]}"
    if act == "list_processes":
        return list_processes()
    if act == "system_info":
        return system_info()
    return f"ERROR: unknown action {act}"


def agent_tool(ws, a, confirm, ask, changed, full=False):
    """Выполняет одно действие агента. Возвращает текст результата для модели.
    Вне папки проекта (режим «Весь ПК») любые изменения всегда требуют подтверждения."""
    act = a["action"]
    try:
        if act == "list_dir":
            p = safe_path(ws, a["path"] or ".", full)
            if not os.path.isdir(p):
                return "ERROR: not a folder"
            items = sorted(os.listdir(p))[:80]
            return "\n".join(("[dir] " if os.path.isdir(os.path.join(p, i)) else "") + i for i in items) or "(empty)"
        if act == "read_file":
            p = safe_path(ws, a["path"], full)
            if not os.path.isfile(p):
                return "ERROR: file not found"
            with open(p, encoding="utf-8", errors="replace") as f:
                if a.get("numbered"):
                    lines = f.read().splitlines()
                else:
                    data = f.read(6001)
                    return data[:6000] + ("\n...[truncated]" if len(data) > 6000 else "")
            st = max(1, _int(a.get("start"), 1))
            en = min(_int(a.get("end"), st + 199), st + 399, len(lines))
            out = "\n".join(f"{n}: {lines[n - 1]}" for n in range(st, en + 1))
            if len(out) > 9000:
                out = out[:9000] + "\n...[truncated]"
            return (out or "(empty)") + (f"\n...[{len(lines)} lines total, use start/end to read more]" if en < len(lines) else "")
        if act == "grep":
            return grep_files(ws, a.get("pattern") or a["path"], a["path"] if a.get("pattern") else ".", full)
        if act == "find_files":
            hits = find_files(a["path"], limit=15, roots=None if full else [ws])
            return "\n".join(hits) or "(nothing found)"
        if act == "open_path":
            p = safe_path(ws, a["path"], full)
            if not os.path.exists(p):
                return "ERROR: not found"
            if os.path.splitext(p)[1].lower() in EXEC_EXT and not confirm(f"Запустить {p}?"):
                return "USER DENIED this action."
            os.startfile(p)
            return f"OK: opened {p}"
        if act == "write_file":
            if not a["blocks"]:
                return "ERROR: CONTENT block missing (use <<< and >>>)"
            p = safe_path(ws, a["path"], full)
            if is_protected(p):
                return "ERROR: system folder, not allowed"
            content = a["blocks"][0].rstrip("\n") + "\n"
            existed = os.path.exists(p)
            preview = content[:700]
            if existed:
                try:
                    with open(p, encoding="utf-8", errors="replace") as f:
                        old_txt = f.read()
                    preview = ("".join(difflib.unified_diff(old_txt.splitlines(True), content.splitlines(True), "было", "станет", n=1))[:900]
                               or "(без изменений)")
                except Exception:
                    pass
            if (ask or not inside(ws, p)) and not confirm(f"{'Перезаписать' if existed else 'Создать'} файл {p} ({content.count(chr(10))} строк)?\n\n{preview}"):
                return "USER DENIED this action."
            backup(p)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            if p not in changed:
                changed.append(p)
            err = syntax_error(content, p)
            return f"OK: wrote {p}" + (f"\nSYNTAX ERROR: {err}. Fix it." if err else "")
        if act == "edit_file":
            if len(a["blocks"]) < 2:
                return "ERROR: need OLD and NEW blocks (use <<< and >>>)"
            p = safe_path(ws, a["path"], full)
            if is_protected(p):
                return "ERROR: system folder, not allowed"
            if not os.path.isfile(p):
                return "ERROR: file not found"
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read()
            old, new = a["blocks"][0], a["blocks"][1]
            n = text.count(old)
            if n == 0:   # модель могла скопировать номера строк из read_file
                strip = lambda t: re.sub(r"(?m)^\d+: ?", "", t)
                if text.count(strip(old)) == 1:
                    old, new, n = strip(old), strip(new), 1
            if n != 1:
                return f"ERROR: OLD text found {n} times, it must be exactly once. Read the file and copy the text exactly."
            if (ask or not inside(ws, p)) and not confirm(f"Изменить {p}?\n\nБыло:\n{old[:350]}\n\nСтанет:\n{new[:350]}"):
                return "USER DENIED this action."
            backup(p)
            new_text = text.replace(old, new, 1)
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_text)
            if p not in changed:
                changed.append(p)
            err = syntax_error(new_text, p)
            return f"OK: edited {p}" + (f"\nSYNTAX ERROR: {err}. Fix it." if err else "")
        if act == "run_command":
            cmd = a["command"]
            if not cmd:
                return "ERROR: COMMAND missing"
            if any(re.search(pat, cmd.lower()) for pat in BLOCKED):
                return "BLOCKED: this command is not allowed."
            if not confirm(f"Выполнить команду в папке проекта?\n\n{cmd}"):
                return "USER DENIED this action."
            return run_cmd(cmd, ws)
        return extra_tool(ws, a, confirm, ask, changed, full)
    except Exception as e:
        return f"ERROR: {e}"


def extract_code(text):
    m = re.search(r"```[\w+#-]*\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip("\n") + "\n"
    return re.sub(r"^```[\w+#-]*\n?", "", text.strip()).strip("`\n ") + "\n"


def syntax_error(code, name):
    if not name.lower().endswith(".py"):
        return None
    try:
        compile(code, name, "exec")
        return None
    except SyntaxError as e:
        return f"{e.msg} (строка {e.lineno})"


def open_in_vscode(path):
    exe = shutil.which("code") or shutil.which("code.cmd")
    if not exe:
        p = os.path.join(LOCAL, "Programs", "Microsoft VS Code", "bin", "code.cmd")
        exe = p if os.path.exists(p) else None
    if exe:
        subprocess.Popen(f'"{exe}" "{path}"', shell=True)
        return True
    os.startfile(os.path.dirname(path))
    return False


def read_text(arg):
    """Читает файл: сначала в известной папке, потом (при «Весь ПК») ищет по всем дискам.
    Возвращает ((путь, текст), "") или (None, ошибка)."""
    key, _, name = arg.partition("|")
    folder = FOLDERS.get(key.strip().lower() or "projects")
    name = fix_ext(os.path.basename(name.strip()))
    path = os.path.join(folder, name) if folder and name else None
    if not path or not os.path.isfile(path):
        found = find_files(name, limit=1, timeout=8) if (FULL and name) else []
        if not found:
            return None, f"Не нашёл файл {name}."
        path = found[0]
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return (path, read_docx(path)[:6000]), ""
    if ext not in READ_EXT and not looks_text(path):
        return None, "Читаю только текстовые файлы, код и docx."
    with open(path, encoding="utf-8", errors="replace") as f:
        return (path, f.read(6000)), ""


class _KBD(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16), ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class _MOU(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32), ("mouseData", ctypes.c_uint32),
                ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class _HW(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_uint32), ("wParamL", ctypes.c_uint16), ("wParamH", ctypes.c_uint16)]


class _IU(ctypes.Union):
    _fields_ = [("ki", _KBD), ("mi", _MOU), ("hi", _HW)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("u", _IU)]


KEYUP, UNICODE = 0x2, 0x4


def _key(vk=0, scan=0, flags=0):
    i = _INPUT()
    i.type = 1   # INPUT_KEYBOARD
    i.u.ki = _KBD(vk, scan, flags, 0, 0)
    return i


def _send(events):
    arr = (_INPUT * len(events))(*events)
    ctypes.windll.user32.SendInput(len(events), arr, ctypes.sizeof(_INPUT))


def hotkey(*vks):
    """Нажимает сочетание клавиш (например Ctrl+K) через SendInput."""
    for vk in vks:
        _send([_key(vk)])
        time.sleep(0.03)
    for vk in reversed(vks):
        _send([_key(vk, 0, KEYUP)])
        time.sleep(0.03)


def type_unicode(text):
    """Печатает текст напрямую в активное окно (без буфера обмена и Ctrl+V), работает с любой раскладкой."""
    ev = []
    for ch in text.replace("\r\n", "\n").replace("\r", "\n"):
        if ch in "\n\t":
            vk = 0x0D if ch == "\n" else 0x09
            ev += [_key(vk), _key(vk, 0, KEYUP)]
        else:
            data = ch.encode("utf-16-le")
            for k in range(0, len(data), 2):
                code = int.from_bytes(data[k:k + 2], "little")
                ev += [_key(0, code, UNICODE), _key(0, code, UNICODE | KEYUP)]
        if len(ev) >= 40:
            _send(ev)
            ev = []
            time.sleep(0.02)
    if ev:
        _send(ev)


def foreground_info():
    u = ctypes.windll.user32
    hwnd = u.GetForegroundWindow()
    pid = ctypes.c_ulong(0)
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    n = u.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    u.GetWindowTextW(hwnd, buf, n + 1)
    return pid.value, buf.value


def wait_foreign_window(timeout=8):
    """Ждёт, пока на передний план выйдет окно НЕ этой программы (чтобы не печатать самим в себя)."""
    end = time.time() + timeout
    while time.time() < end:
        pid, title = foreground_info()
        if pid and pid != os.getpid() and title:
            return True, title
        time.sleep(0.4)
    return False, ""


def split_msg(arg):
    rec, _, txt = arg.partition("|")
    return rec.strip(), txt.strip()


def describe_plan(steps):
    lines = []
    for s in steps:
        a, arg = s["action"], s["arg"]
        if a == "open_app":
            lines.append(f"• открыть: {arg}")
        elif a == "type_text":
            lines.append(f"• напечатать в открытой программе: «{arg[:200]}»")
        elif a == "telegram_message":
            rec, txt = split_msg(arg)
            lines.append(f"• написать в Telegram: кому — {rec}, текст — «{txt[:200]}»")
        else:
            lines.append(f"• {a} {arg}".strip())
    text = "Выполнить план?\n\n" + "\n".join(lines)
    if any(s["action"] == "telegram_message" and not re.fullmatch(r"@?[A-Za-z][A-Za-z0-9_]{4,31}", split_msg(s["arg"])[0]) for s in steps):
        text += "\n\nКонтакт будет выбран через поиск Telegram (первый результат)."
    return text + "\n\nПосле «Да» не трогай мышь и клавиатуру, пока всё не выполнится."


def press_key(vk, times=1):
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)


def run_action(action, arg, confirm):
    """Выполняет разрешённое действие. Возвращает (успех, сообщение). Сообщение пишет программа, а не модель."""
    arg = (arg or "").strip()
    if action == "open_app":
        key = arg.lower()
        if key not in APPS:
            close = difflib.get_close_matches(key, list(APPS), n=1, cutoff=0.75)
            key = close[0] if close else None
        if not key:
            return False, f"Не знаю программу «{arg}». Добавь её в APPS."
        subprocess.Popen(f'start "" {APPS[key]}', shell=True)
        return True, f"Открываю {key}."
    if action == "open_url":
        if arg.startswith(("http://", "https://")):
            webbrowser.open(arg)
            return True, "Открываю ссылку в браузере."
        return False, "Ссылка должна начинаться с http(s)."
    if action == "set_wallpaper":
        os.makedirs(WALL_DIR, exist_ok=True)
        files = [f for f in os.listdir(WALL_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        if not files:
            return False, f"В папке {WALL_DIR} нет картинок. Добавь туда файлы."
        pick = [f for f in files if arg.lower() in f.lower()] if arg and arg != "random" else files
        name = random.choice(pick or files)
        ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.join(WALL_DIR, name), 3)
        return True, f"Обои сменены: {name}"
    if action == "set_wallpaper_url":
        if not arg.startswith(("http://", "https://")):
            return False, "Нужна прямая ссылка на картинку."
        try:
            req = urllib.request.Request(arg, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
                ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/bmp": ".bmp"}.get(ctype)
                if not ext:
                    return False, "По ссылке не картинка (нужен jpg, png или bmp). Нужна прямая ссылка на файл."
                data = r.read(30_000_001)
            if len(data) > 30_000_000:
                return False, "Файл слишком большой."
        except Exception as e:
            return False, f"Не удалось скачать: {e}"
        os.makedirs(WALL_DIR, exist_ok=True)
        name = f"web_{int(time.time())}{ext}"
        path = os.path.join(WALL_DIR, name)
        with open(path, "wb") as f:
            f.write(data)
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        return True, f"Обои установлены из ссылки (сохранены как {name})."
    if action == "volume":
        parts = arg.lower().split()
        if parts and parts[0] == "mute":
            press_key(0xAD)
            return True, "Звук включён или выключен."
        if len(parts) == 2 and parts[0] in ("up", "down") and parts[1].isdigit():
            n = min(int(parts[1]), 25)
            press_key(0xAF if parts[0] == "up" else 0xAE, n)
            return True, f"Громкость {'+' if parts[0] == 'up' else '-'}{n * 2}%."
        return False, "Не понял громкость."
    if action == "list_files":
        folder = FOLDERS.get(arg.lower()) or (arg if FULL and os.path.isdir(arg) else None)
        if not folder or not os.path.isdir(folder):
            return False, "Не нашёл такую папку."
        items = sorted(os.listdir(folder))
        text = "\n".join(items[:40]) if items else "(пусто)"
        return True, f"{folder}:\n{text}" + (f"\n... и ещё {len(items) - 40}" if len(items) > 40 else "")
    if action == "open_folder":
        folder = FOLDERS.get(arg.lower())
        if not folder or not os.path.isdir(folder):
            return False, "Не нашёл такую папку."
        os.startfile(folder)
        return True, f"Открываю {folder}."
    if action == "save_wallpaper":
        buf = ctypes.create_unicode_buffer(520)
        ctypes.windll.user32.SystemParametersInfoW(0x73, 520, buf, 0)
        if not buf.value or not os.path.isfile(buf.value):
            return False, "Не нашёл файл текущих обоев."
        os.makedirs(WALL_DIR, exist_ok=True)
        dest = os.path.join(WALL_DIR, f"current_{int(time.time())}{os.path.splitext(buf.value)[1] or '.jpg'}")
        shutil.copy2(buf.value, dest)
        return True, f"Текущие обои сохранены: {dest}"
    if action == "delete_file":
        key, _, name = arg.partition("|")
        folder = FOLDERS.get(key.strip().lower() or "projects")
        name = fix_ext(os.path.basename(name.strip()))
        path = os.path.join(folder, name) if folder and name else None
        if not path or not os.path.isfile(path):
            found = find_files(name, limit=1, timeout=8) if (FULL and name) else []
            path = found[0] if found else None
        if not path or not os.path.isfile(path):
            return False, f"Файл {name} не найден."
        if is_protected(path):
            return False, "Системные папки трогать нельзя."
        if not confirm(f"Убрать файл {path} в папку {TRASH_DIR}?"):
            return False, "Отменено."
        os.makedirs(TRASH_DIR, exist_ok=True)
        dest = os.path.join(TRASH_DIR, f"{int(time.time())}_{os.path.basename(path)}")
        shutil.move(path, dest)
        return True, f"Файл перемещён в {dest}. Он не стёрт насовсем, при желании удали его оттуда сам."
    if action == "open_file":
        name, _, prog = arg.partition("|")
        name, prog = fix_ext(name.strip().strip("\"'")), prog.strip().lower()
        path = name if os.path.exists(name) else None
        more = []
        if not path:
            found = find_files(name, limit=4) if FULL else find_files(name, limit=4, roots=[CODE_DIR])
            if not found:
                return False, f"Не нашёл «{name}» на дисках."
            path, more = found[0], found[1:]
        if os.path.isfile(path) and prog in APPS and not APPS[prog].endswith(":") and "://" not in APPS[prog]:
            subprocess.Popen(f'start "" {APPS[prog]} "{path}"', shell=True)
        else:
            if os.path.splitext(path)[1].lower() in EXEC_EXT and not confirm(f"Запустить {path}?"):
                return False, "Отменено."
            os.startfile(path)
        return True, f"Открываю: {path}" + (("\nЕщё нашёл:\n" + "\n".join(more)) if more else "")
    if action == "close_app":
        proc = PROCS.get(arg.lower())
        if not proc:
            return False, f"Не знаю, как закрыть «{arg}»."
        r = subprocess.run(["taskkill", "/IM", proc, "/T"], capture_output=True)
        return (r.returncode == 0), (f"Закрываю {arg}." if r.returncode == 0 else f"{arg} сейчас не запущен.")
    if action == "say":
        return False, arg
    if action == "lock":
        ctypes.windll.user32.LockWorkStation()
        return True, "Блокирую ПК."
    if action in ("shutdown", "restart"):
        if not confirm(f"Точно {'выключить' if action == 'shutdown' else 'перезагрузить'} ПК?"):
            return False, "Отменено."
        subprocess.Popen(["shutdown", "/s" if action == "shutdown" else "/r", "/t", "10"])
        return True, "ПК выключится через 10 секунд. Отмена: shutdown /a"
    return False, f"Неизвестное действие: {action}"


class App:
    def __init__(self, root):
        self.root = root
        self.workspace = CODE_DIR
        self.cfg = {"level": 1, "agent": False, "ask": True, "full": True, "ws": CODE_DIR, "files": []}
        self.attachments = []
        root.title("Мой ИИ")
        root.geometry("1000x640")
        root.minsize(960, 480)
        root.configure(bg="#1e1e1e")
        bottom = tk.Frame(root, bg="#1e1e1e")
        bottom.pack(side="bottom", fill="x", padx=8, pady=8)
        self.entry = tk.Entry(bottom, bg="#333333", fg="white", insertbackground="white", font=("Segoe UI", 12), bd=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.stop_btn = tk.Button(bottom, text="Стоп", command=self.on_stop, state="disabled", bg="#c62828", fg="white", bd=0, padx=14)
        self.stop_btn.pack(side="right", padx=(8, 0), ipady=4)
        self.status = tk.Label(root, text="", bg="#1e1e1e", fg="#9e9e9e", anchor="w")
        self.status.pack(side="bottom", fill="x", padx=10)
        top = tk.Frame(root, bg="#1e1e1e")
        top.pack(side="top", fill="x", padx=8, pady=(8, 0))
        tk.Label(top, text="Режим:", bg="#1e1e1e", fg="#9e9e9e").pack(side="left")
        self.level_box = ttk.Combobox(top, values=LEVELS, state="readonly", width=10)
        self.level_box.current(1)
        self.level_box.pack(side="left", padx=(4, 10))
        tk.Label(top, text="Модель:", bg="#1e1e1e", fg="#9e9e9e").pack(side="left")
        self.model_box = ttk.Combobox(top, values=[], state="readonly", width=16, postcommand=self.refresh_models)
        self.model_box.pack(side="left", padx=(4, 10))
        self.model_box.bind("<<ComboboxSelected>>", self.on_model)
        cb = dict(bg="#1e1e1e", fg="#e6e6e6", selectcolor="#333333", activebackground="#1e1e1e", activeforeground="white", bd=0)
        self.agent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="Агент (файлы и команды)", variable=self.agent_var, **cb).pack(side="left")
        self.full_var = tk.BooleanVar(value=True)
        tk.Checkbutton(top, text="Весь ПК", variable=self.full_var, **cb).pack(side="left", padx=(8, 0))
        top2 = tk.Frame(root, bg="#1e1e1e")
        top2.pack(side="top", fill="x", padx=8, pady=(4, 0))
        self.ask_var = tk.BooleanVar(value=True)
        tk.Checkbutton(top2, text="подтверждать правки", variable=self.ask_var, **cb).pack(side="left")
        tk.Button(top2, text="📎 Файл", command=self.attach, bg="#333333", fg="white", bd=0, padx=8).pack(side="left", padx=(10, 0))
        tk.Button(top2, text="✕", command=self.clear_attach, bg="#333333", fg="white", bd=0, padx=6).pack(side="left", padx=(4, 0))
        self.attach_label = tk.Label(top2, text="", bg="#1e1e1e", fg="#ffcc80", anchor="w")
        self.attach_label.pack(side="left", padx=6)
        tk.Button(top2, text="Папка проекта…", command=self.pick_ws, bg="#333333", fg="white", bd=0, padx=8).pack(side="right")
        self.ws_label = tk.Label(root, text="", bg="#1e1e1e", fg="#9e9e9e", anchor="w")
        self.ws_label.pack(side="top", fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(root, bg="#252526", fg="#e6e6e6", font=("Segoe UI", 11), wrap="word", state="disabled", bd=0, height=10)
        self.log.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.log.tag_config("me", foreground="#4fc3f7")
        self.log.tag_config("ai", foreground="#a5d6a7")
        self.log.tag_config("sys", foreground="#9e9e9e")
        self.log.tag_config("think", foreground="#7a7a7a", font=("Segoe UI", 10, "italic"))
        self.log.tag_config("code", foreground="#ffcc80", font=("Consolas", 10))
        self.entry.bind("<Return>", self.send)
        self.entry.focus()
        if TkinterDnD:   # перетаскивание файлов в окно (нужен pip install tkinterdnd2)
            try:
                for w in (self.log, self.entry):
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind("<<Drop>>", self.on_drop)
            except Exception:
                pass
        self.q = queue.Queue()
        self.stop = threading.Event()
        self.history, self.last = [], None   # last = последний написанный файл {"name", "code"}
        self.busy = False
        self.model_shown = False
        self.load()
        self.apply_settings()
        self.say("Пиши свободно: вопросы, команды («открой дискорд», «громче на 10»), файлы («открой блокнот с именем ошибки.txt», "
                 "«найди файл отчёт», «прочитай snake.py»), код («напиши змейку»). Файлы для разбора прикрепляй кнопкой «📎 Файл» "
                 "(или перетаскивай, если установлен tkinterdnd2). Модель, режим, «Агент» и «Весь ПК» — сверху. /clear забывает всё.", "sys", log=False)
        if self.history:
            self.say(f"Загружена история: {len(self.history)} сообщений (в окне последние 30). Полный журнал: {CHAT_LOG}", "sys", log=False)
            for m in self.history[-30:]:
                mine = m["role"] == "user"
                self.say(("Ты: " if mine else "ИИ: ") + m["content"][:1200], "me" if mine else "ai", log=False)
        self.root.after(100, self.poll)

    # --- память между запусками ---
    def load(self):
        try:
            with open(HIST_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self.history = [m for m in data.get("history", [])[-MAX_HISTORY:] if not CJK.search(m.get("content", ""))]
            self.last = data.get("last")
            self.cfg.update(data.get("settings", {}))
            self.workspace = self.cfg.get("ws") or CODE_DIR
        except Exception:
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(HIST_FILE), exist_ok=True)
            with open(HIST_FILE, "w", encoding="utf-8") as f:
                json.dump({"history": self.history[-MAX_HISTORY:], "last": self.last,
                           "settings": {k: v for k, v in self.cfg.items() if k != "files"}}, f, ensure_ascii=False)
        except Exception:
            pass

    # --- вывод в окно ---
    def _log(self, text):
        try:
            os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
            with open(CHAT_LOG, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass

    def say(self, text, tag, log=True):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n\n", tag)
        self.log.config(state="disabled")
        self.log.see("end")
        if log:
            self._log(text + "\n\n")

    def put(self, text, tag):
        self.log.config(state="normal")
        self.log.insert("end", text, tag)
        self.log.config(state="disabled")
        self.log.see("end")
        self._log(text)

    # --- ввод ---
    def send(self, _=None):
        text = self.entry.get().strip()
        if not text or self.busy:
            return
        self.entry.delete(0, "end")
        if text.lower() == "/undo":
            self.say(undo_last(), "sys")
            return
        if text.lower() == "/clear":
            self.history, self.last = [], None
            self.save()
            self.say("История очищена.", "sys")
            return
        self.snapshot_cfg()
        self.cur_text = text   # чистый текст без пометок о файлах: по нему разбираются команды
        shown = text + (("\n📎 " + ", ".join(os.path.basename(p) for p in self.cfg["files"])) if self.cfg["files"] else "")
        self.say("Ты: " + shown, "me")
        self.history.append({"role": "user", "content": shown})
        self.attachments = []
        self.refresh_attach()
        self.busy = True
        self.stop.clear()
        self.stop_btn.config(state="normal")
        self.status.config(text="думаю...")
        threading.Thread(target=self.work, daemon=True).start()

    def on_stop(self):
        self.stop.set()
        self.status.config(text="останавливаю...")

    def confirm(self, text):
        ev, box = threading.Event(), {}
        self.q.put(("confirm", text, ev, box))
        ev.wait()
        return box.get("ok", False)

    # --- настройки и агент ---
    def apply_settings(self):
        global MODEL, CODE_MODEL
        if self.cfg.get("model"):
            MODEL = CODE_MODEL = self.cfg["model"]
        self.model_box.set(MODEL)
        lvl = self.cfg.get("level", 1)
        self.level_box.current(lvl if isinstance(lvl, int) and 0 <= lvl < len(LEVELS) else 1)
        self.agent_var.set(bool(self.cfg.get("agent", False)))
        self.ask_var.set(bool(self.cfg.get("ask", True)))
        self.full_var.set(bool(self.cfg.get("full", True)))
        self.ws_label.config(text=f"Проект: {self.workspace}")

    def snapshot_cfg(self):
        # настройки копируем в обычный словарь здесь (в главном потоке), поток работы читает только его
        global FULL
        lvl = self.level_box.current()
        self.cfg = {"level": lvl if lvl >= 0 else 1, "agent": bool(self.agent_var.get()), "ask": bool(self.ask_var.get()),
                    "full": bool(self.full_var.get()), "ws": os.path.abspath(self.workspace), "model": MODEL,
                    "files": list(self.attachments)}
        FULL = self.cfg["full"]

    def refresh_models(self):
        try:
            with urllib.request.urlopen(API + "/api/tags", timeout=3) as r:
                names = [m["name"] for m in json.loads(r.read()).get("models", [])]
            if names:
                self.model_box["values"] = names
        except Exception:
            pass

    def on_model(self, _=None):
        global MODEL, CODE_MODEL, THINKS
        new = self.model_box.get()
        if self.busy:
            self.say("Подожди, пока закончится текущий ответ.", "sys")
            self.model_box.set(MODEL)
            return
        old, MODEL, CODE_MODEL, THINKS = MODEL, new, new, None
        self.cfg["model"] = new
        self.model_shown = False
        self.save()
        self.say(f"Модель переключена на {new}.", "sys")
        if old and old != new:   # выгружаем старую из памяти, чтобы не держать две модели сразу
            def unload():
                try:
                    post("/api/generate", {"model": old, "keep_alive": 0}, 15).close()
                except Exception:
                    pass
            threading.Thread(target=unload, daemon=True).start()

    def set_clip(self, text):
        ev = threading.Event()
        self.q.put(("clip", text, ev))
        ev.wait(5)

    def type_into_active(self, text):
        ok, title = wait_foreign_window(8)   # ждём, пока откроется нужная программа (а не печатаем в себя)
        if not ok:
            return False, "Не вижу открывшегося окна программы, печатать некуда. Попробуй ещё раз."
        time.sleep(0.8)
        type_unicode(text)
        return True, f"Напечатано в окно «{title}»."

    def telegram_send(self, arg):
        rec, txt = split_msg(arg)
        user = re.fullmatch(r"@?([A-Za-z][A-Za-z0-9_]{4,31})", rec)
        if user:   # точное имя пользователя: открываем чат ссылкой
            os.startfile(f"tg://resolve?domain={user.group(1)}")
        else:
            subprocess.Popen(f'start "" {TELEGRAM}', shell=True)
        ok, title = wait_foreign_window(10)
        if not ok:
            return False, "Telegram не открылся."
        time.sleep(3)
        if not user:   # обычное имя: поиск Telegram (Ctrl+K), берём первый результат
            hotkey(0x11, 0x4B)
            time.sleep(0.8)
            type_unicode(rec)
            time.sleep(1.5)
            if self.stop.is_set():
                return False, "Остановлено."
            hotkey(0x0D)
            time.sleep(1.2)
        if self.stop.is_set():
            return False, "Остановлено."
        type_unicode(txt)
        time.sleep(0.4)
        hotkey(0x0D)
        return True, f"Сообщение отправлено: {rec}. Проверь в Telegram."

    # --- прикреплённые файлы ---
    def attach(self):
        self.add_files(filedialog.askopenfilenames(title="Прикрепить файлы"))

    def add_files(self, paths):
        for p in paths:
            if os.path.isfile(p) and p not in self.attachments:
                self.attachments.append(p)
        self.refresh_attach()

    def clear_attach(self):
        self.attachments = []
        self.refresh_attach()

    def refresh_attach(self):
        names = ", ".join(os.path.basename(p) for p in self.attachments)
        self.attach_label.config(text=("прикреплено: " + names) if names else "")

    def on_drop(self, event):
        self.add_files(self.root.tk.splitlist(event.data))

    def pick_ws(self):
        d = filedialog.askdirectory(initialdir=self.workspace, title="Папка проекта для агента")
        if d:
            self.workspace = os.path.abspath(d)
            self.cfg["ws"] = self.workspace
            self.ws_label.config(text=f"Проект: {self.workspace}")
            self.save()

    def agent(self, task, extra=""):
        t = task.strip()
        if VAGUE.match(t):
            if getattr(self, "last_task", None):
                task = f"{self.last_task}\n(The user now says «{t}»: continue or redo the previous task.)"
            else:
                self.q.put(("msg", "ИИ: Не понял, что делать. Опиши задачу: что сделать и с каким файлом.", "ai"))
                return
        else:
            self.last_task = t
        if "tools" in model_caps(MODEL):
            try:
                return self.agent_native(task, extra)
            except urllib.error.HTTPError as e:
                if e.code != 400:
                    raise
                self.q.put(("msg", "Модель не поддерживает вызов инструментов, работаю в текстовом режиме.", "sys"))
        return self.agent_text(task, extra)

    def agent_native(self, task, extra=""):
        ws, lvl, full = self.cfg["ws"], self.cfg["level"], self.cfg.get("full", True)
        if not os.path.isdir(ws):
            self.q.put(("msg", f"Папка проекта не найдена: {ws}. Выбери её кнопкой «Папка проекта…».", "sys"))
            return
        changed = []
        try:
            items = sorted(os.listdir(ws))[:60]
        except Exception:
            items = []
        listing = "\n".join(("[dir] " if os.path.isdir(os.path.join(ws, i)) else "") + i for i in items) or "(empty)"
        system = AGENT_RULES + (" Full PC access is on: you may use absolute Windows paths anywhere. Changes outside the project folder "
                                "always need the user's approval." if full else "")
        kf = known_folders()
        FOLDERS.update({k: v for k, v in kf.items() if k in ("desktop", "documents")})
        system += (" To DO anything on the PC you must call tools; never say something is done unless a tool result confirms it. "
                   "Relative paths are inside the project folder; for other places use absolute paths. Known folders: "
                   + "; ".join(f"{k}={kf[k]}" for k in ("desktop", "documents", "downloads", "projects")) + ".")
        for fn in ("AGENTS.md", "CLAUDE.md"):   # инструкции проекта, как в Claude Code / Codex
            fp = os.path.join(ws, fn)
            if os.path.isfile(fp):
                with open(fp, encoding="utf-8", errors="replace") as f:
                    system += f"\n\nProject instructions ({fn}):\n" + f.read(2000)
                break
        user = (f"Project folder: {ws}\nContents:\n{listing}\n\n" + (f"Attached files:\n{extra}\n\n" if extra else "") + f"Task: {task}")
        if lvl >= 2:
            self.q.put(("status", "агент: составляю план..."))
            plan = complete(MODEL, [{"role": "system", "content": "Write a short numbered plan (max 6 steps) for the task. No code."},
                                    {"role": "user", "content": user}], self.stop, 0.3, 300, think=False)
            if self.stop.is_set():
                return
            user += f"\n\nPlan:\n{plan}"
        msgs = [{"role": "system", "content": system}] + self.history[-7:-1] + [{"role": "user", "content": user}]
        base, limit, reviewed, final, used, nudged = len(msgs), AGENT_STEPS[lvl], False, None, False, False
        for i in range(limit):
            if self.stop.is_set():
                break
            while sum(len(m.get("content") or "") for m in msgs) > 16000 and len(msgs) > base + 2:
                del msgs[base]
                while base < len(msgs) and msgs[base]["role"] == "tool":
                    del msgs[base]
            self.q.put(("status", f"агент: шаг {i + 1}/{limit}..."))
            text, calls = chat_tools(MODEL, msgs, self.stop, think=(lvl == 3) if THINKS else None,
                                     on_think=lambda t: self.q.put(("stream", t, "think")))
            if self.stop.is_set():
                break
            text = text.strip()
            msgs.append({"role": "assistant", "content": text, "tool_calls": calls} if calls else {"role": "assistant", "content": text})
            if not calls:
                if not used and not nudged and re.search(r"успешн|перемещ|созда[нл]|удал[ёе]н|готов|сделал|выполнен|открыл|отправил|done|moved|created", text.lower()):
                    nudged = True   # модель заявила, что сделала, но ни одного инструмента не вызвала
                    msgs.append({"role": "user", "content": "You have not called any tool, so nothing was done. Call the right tool now, "
                                                            "or tell the user honestly that you cannot do it."})
                    continue
                if lvl == 3 and changed and not reviewed:
                    reviewed = True
                    msgs.append({"role": "user", "content": "Before finishing, re-read the files you changed, check them for bugs and run them if possible."})
                    continue
                final = text or ("Готово." if used else "Модель ничего не ответила. Переформулируй задачу.")
                break
            for c in calls:
                fn = c.get("function", {})
                name = fn.get("name", "")
                if name not in TOOL_NAMES:
                    result = f"ERROR: unknown tool {name}"
                else:
                    used = True
                    a = tool_args(name, fn.get("arguments"))
                    if name == "telegram_message":
                        rec, txt = str(a["args"].get("recipient") or "").strip(), str(a["args"].get("text") or "").strip()
                        if not (rec and txt):
                            result = "ERROR: recipient and text are required"
                        elif not self.confirm(describe_plan([{"action": "telegram_message", "arg": f"{rec} | {txt}"}])):
                            result = "USER DENIED this action."
                        else:
                            self.q.put(("status", "пишу в Telegram, не трогай мышь и клавиатуру..."))
                            result = self.telegram_send(f"{rec} | {txt}")[1]
                    elif name == "todo":
                        items = a["args"].get("items") or []
                        if isinstance(items, str):
                            items = [x for x in re.split(r"[\n;]", items) if x.strip()]
                        self.q.put(("msg", "📋 План:\n" + "\n".join("• " + str(x) for x in items), "sys"))
                        result = "OK"
                    else:
                        result = agent_tool(ws, a, self.confirm, self.cfg["ask"], changed, full)
                    self.q.put(("msg", f"▶ {name} {a['path'] or a['command'] or a['pattern']} → {result[:200]}", "sys"))
                msgs.append({"role": "tool", "tool_name": name, "content": result[:6000]})
        else:
            self.q.put(("msg", "Достигнут лимит шагов. Напиши «продолжай», если нужно.", "sys"))
        if final:
            self.q.put(("msg", "ИИ: " + final, "ai"))
            self.history.append({"role": "assistant", "content": "[агент] " + final})
        elif changed:
            self.history.append({"role": "assistant", "content": f"[агент] изменено файлов: {len(changed)}"})
        if changed:
            self.q.put(("msg", "Изменённые файлы (отмена: /undo):\n" + "\n".join(changed), "sys"))
            open_in_vscode(changed[-1])

    def agent_text(self, task, extra=""):
        ws, lvl, full = self.cfg["ws"], self.cfg["level"], self.cfg.get("full", True)
        if not os.path.isdir(ws):
            self.q.put(("msg", f"Папка проекта не найдена: {ws}. Выбери её кнопкой «Папка проекта…».", "sys"))
            return
        changed = []
        try:
            items = sorted(os.listdir(ws))[:60]
        except Exception:
            items = []
        listing = "\n".join(("[dir] " if os.path.isdir(os.path.join(ws, i)) else "") + i for i in items) or "(empty)"
        system = AGENT_SYSTEM + (" Full PC access is on: you may use absolute Windows paths anywhere (for example D:\\folder\\file.txt), "
                                 "find_files searches all drives and open_path opens a file or folder. "
                                 "Changes outside the project folder always need the user's approval." if full else "")
        head = [{"role": "system", "content": system}] + self.history[-7:-1] + \
               [{"role": "user", "content": f"Project folder contents:\n{listing}\n\n" +
                 (f"Attached files:\n{extra}\n\n" if extra else "") + f"Task: {task}"}]
        if lvl >= 2:
            self.q.put(("status", "агент: составляю план..."))
            plan = complete(MODEL, [{"role": "system", "content": "Write a short numbered plan (max 6 steps) for the task. No code."}, head[-1]],
                            self.stop, 0.3, 300, think=False)
            if self.stop.is_set():
                return
            head[-1] = {"role": "user", "content": head[-1]["content"] + f"\n\nPlan:\n{plan}"}
        tail, bad, reviewed, final = [], 0, False, None
        limit = AGENT_STEPS[lvl]
        for i in range(limit):
            if self.stop.is_set():
                break
            while sum(len(m["content"]) for m in head + tail) > 22000 and len(tail) > 2:
                del tail[:2]
            self.q.put(("status", f"агент: шаг {i + 1}/{limit}..."))
            self.q.put(("stream", f"▶ шаг {i + 1}\n", "sys"))
            out = []
            for piece in stream(MODEL, head + tail, self.stop, 0.2, think=(lvl == 3) if THINKS else None,
                                on_think=lambda t: self.q.put(("stream", t, "think"))):
                out.append(piece)
                self.q.put(("stream", piece, "code"))
            self.q.put(("stream", "\n\n", "code"))
            if self.stop.is_set():
                break
            raw = "".join(out)
            a = parse_action(raw)
            tail.append({"role": "assistant", "content": raw})
            if not a or a["action"] not in AGENT_ACTIONS:
                bad += 1
                if bad > 2:
                    self.q.put(("msg", "Модель не смогла ответить в нужном формате. Попробуй режим выше или переформулируй задачу.", "sys"))
                    break
                tail.append({"role": "user", "content": "Format error. Reply with exactly one ACTION block as described."})
                continue
            if a["action"] == "final":
                if lvl == 3 and changed and not reviewed:
                    reviewed = True
                    tail.append({"role": "user", "content": "Before finishing, re-read the files you changed and check them for bugs, "
                                                            "and run them if possible. If everything is fine, reply with final again."})
                    continue
                final = a["message"] or "Готово."
                break
            result = agent_tool(ws, a, self.confirm, self.cfg["ask"], changed, full)
            self.q.put(("msg", f"[{a['action']}] {a['path'] or a['command']} → {result[:300]}", "sys"))
            tail.append({"role": "user", "content": "RESULT:\n" + result})
        else:
            self.q.put(("msg", "Достигнут лимит шагов. Напиши «продолжай», если нужно.", "sys"))
        if final:
            self.q.put(("msg", "ИИ: " + final, "ai"))
            self.history.append({"role": "assistant", "content": "[агент] " + final})
        elif changed:
            self.history.append({"role": "assistant", "content": f"[агент] изменено файлов: {len(changed)}"})
        if changed:
            self.q.put(("msg", "Изменённые файлы:\n" + "\n".join(changed), "sys"))
            open_in_vscode(changed[-1])

    # --- работа в потоке ---
    def chat_answer(self, extra=None, images=None):
        msgs = [{"role": "system", "content": CHAT_SYSTEM}] + self.history[-10:]
        content = msgs[-1]["content"]
        if extra:
            content = extra + "\n\n" + content
        msgs[-1] = {"role": "user", "content": content + "\n\n(Ответь по-русски.)"}
        if images:
            msgs[-1]["images"] = images
        lvl = self.cfg["level"]
        if lvl == 0:   # Flash: коротко и быстро
            msgs[0] = {"role": "system", "content": CHAT_SYSTEM + " Answer in 1-3 short sentences."}
        native = bool(THINKS) and lvl >= 2   # у модели есть своё размышление: используем его
        if lvl >= 2 and not native:   # иначе скрытое размышление отдельным запросом
            self.q.put(("status", "размышляю (1/%d)..." % (2 if lvl == 2 else 3)))
            notes = complete(MODEL, with_note(msgs, "Think step by step about the best answer. Write your reasoning briefly "
                                              "(up to 150 words). Do not write the final answer yet."), self.stop, 0.3, 300)
            if self.stop.is_set():
                return
            if lvl == 3:
                self.q.put(("status", "черновик (2/3)..."))
                draft = complete(MODEL, with_note(msgs, f"Reasoning notes:\n{notes}\n\nWrite a draft answer."), self.stop, 0.3, 600)
                if self.stop.is_set():
                    return
                msgs = with_note(msgs, f"Reasoning notes:\n{notes}\n\nDraft answer:\n{draft}\n\nCheck the draft for mistakes and give the improved final answer.")
                self.q.put(("status", "проверяю и отвечаю (3/3)..."))
            else:
                msgs = with_note(msgs, f"Private reasoning notes (not for the user):\n{notes}\n\nNow give the final answer.")
                self.q.put(("status", "отвечаю (2/2)..."))
        if native and lvl == 3:   # Максимум со встроенным размышлением: быстрый черновик, потом проверка с размышлением
            self.q.put(("status", "черновик (1/2)..."))
            draft = complete(MODEL, with_note(msgs, "Write a draft answer."), self.stop, 0.3, 600, think=False)
            if self.stop.is_set():
                return
            msgs = with_note(msgs, f"Draft answer:\n{draft}\n\nCheck the draft for mistakes and give the improved final answer.")
            self.q.put(("status", "проверяю и отвечаю (2/2)..."))
        self.q.put(("stream", "ИИ: ", "ai"))
        out, thought = [], []

        def on_think(t):
            thought.append(t)
            self.q.put(("stream", t, "think"))
        think = (lvl >= 2) if THINKS else None   # на Flash и Среднем размышление выключено
        for piece in stream(MODEL, msgs, self.stop, 0.3, 250 if lvl == 0 else None, think=think, on_think=on_think):
            if thought and not out:
                self.q.put(("stream", "\n\n", "ai"))
            out.append(piece)
            self.q.put(("stream", piece, "ai"))
        self.q.put(("stream", "\n\n", "ai"))
        text = "".join(out)
        if not text.strip():
            if not self.stop.is_set():
                self.q.put(("msg", "Модель вернула пустой ответ. Попробуй ещё раз или выбери режим выше.", "sys"))
        elif CJK.search(text):   # китайский ответ в историю не сохраняем, чтобы модель не копировала его
            self.q.put(("msg", "Модель ответила не по-русски. Напиши ещё раз или перефразируй.", "sys"))
        else:
            self.history.append({"role": "assistant", "content": text})

    def make_code(self, arg):
        if "|" in arg:
            name, _, task = arg.partition("|")
        else:
            name, task = "", arg
        name = os.path.basename(name.strip()) or (self.last["name"] if self.last else "program.py")
        name = re.sub(r"[^\w.\-]", "_", name)
        if os.path.splitext(name)[1].lower() not in ALLOWED_EXT:
            name = os.path.splitext(name)[0] + ".py"
        user = f"File: {name}\nTask: {task.strip() or 'a small program'}"
        if self.last and self.last["name"] == name:
            user += f"\nCurrent code to modify:\n```\n{self.last['code']}\n```"
        msgs = [{"role": "system", "content": CODE_SYSTEM}, {"role": "user", "content": user}]
        err = None
        for attempt in range(CODE_TRIES[self.cfg["level"]]):   # вторая попытка: если в коде синтаксическая ошибка, просим исправить
            self.q.put(("msg", f"Пишу {name}..." if attempt == 0 else f"В коде ошибка ({err}), исправляю...", "sys"))
            out = []
            think = (self.cfg["level"] >= 2) if THINKS else None
            for piece in stream(CODE_MODEL, msgs, self.stop, 0.2, think=think,
                                on_think=lambda t: self.q.put(("stream", t, "think"))):
                out.append(piece)
                self.q.put(("stream", piece, "code"))
            self.q.put(("stream", "\n\n", "code"))
            if self.stop.is_set():
                return "Остановлено, файл не сохранён."
            raw = "".join(out)
            code = extract_code(raw)
            err = syntax_error(code, name)
            if not err:
                break
            msgs = msgs + [{"role": "assistant", "content": raw},
                           {"role": "user", "content": f"The code has a syntax error: {err}. Fix it and return the full corrected file in one code block."}]
        os.makedirs(CODE_DIR, exist_ok=True)
        base, ext = os.path.splitext(name)
        path, n = os.path.join(CODE_DIR, name), 2
        while os.path.exists(path):
            path = os.path.join(CODE_DIR, f"{base}_{n}{ext}")
            n += 1
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        self.last = {"name": name, "code": code}
        ok = open_in_vscode(path)
        msg = f"Файл сохранён: {path}" + ("" if ok else " (VS Code не найден, открыта папка)")
        if name.endswith(".py"):
            msg += f"\nЗапуск: python \"{path}\""
        if err:
            msg += f"\nВнимание: в коде осталась синтаксическая ошибка: {err}. Скинь её Клоду, он поможет."
        self.q.put(("msg", msg, "sys"))
        return f"Создан файл {name}."

    def validate(self, steps, text):
        t = text.lower()
        good = []
        for s in steps:
            action = str(s.get("action", ""))
            if action not in VALID:
                continue
            if action == "write_code" and (not any(w in t for w in WRITE_WORDS) or re.search(r"телеграм|telegram|сообщени|в тг", t)):
                continue
            if action in ("open_url", "set_wallpaper_url") and str(s.get("arg", "")) not in text:
                continue   # ссылки, которых нет в твоём сообщении, модель придумала сама
            if action in ("read_file", "delete_file") and (s.get("arg", "").partition("|")[2].strip().lower() not in t
                                                            or not s.get("arg", "").partition("|")[2].strip()):
                continue   # имя файла должно быть в твоём сообщении
            if action == "shutdown" and not re.search(r"выключ\w* (компьютер|пк|комп|ноут)|заверши\w* работу|выруби", t):
                continue   # выключение только по прямой просьбе
            if action == "restart" and "перезагруз" not in t:
                continue
            if action == "lock" and not re.search(r"заблокир|блокиров|lock", t):
                continue
            if action == "open_file":
                stem = os.path.splitext(fix_ext(str(s.get("arg", "")).partition("|")[0].strip().lower()))[0]
                if not stem or stem not in t:
                    continue   # имени файла нет в твоём сообщении: модель его придумала
            if action == "close_app" and str(s.get("arg", "")).lower() not in PROCS:
                continue
            good.append({"action": action, "arg": str(s.get("arg", ""))})
        if any(g["action"] == "telegram_message" for g in good):   # Telegram открывается внутри самого действия
            good = [g for g in good if not (g["action"] == "open_app" and g["arg"].lower() in ("telegram", "телеграм"))]
        return good or [{"action": "chat", "arg": ""}]

    def work(self):
        text = getattr(self, "cur_text", None) or self.history[-1]["content"]
        try:
            if not ensure_server():
                self.q.put(("msg", "Не удалось запустить Ollama. Проверь путь OLLAMA_EXE.", "sys"))
                return
            if not pick_model():
                self.q.put(("msg", "В Ollama не найдено ни одной модели. Проверь команду ollama list.", "sys"))
                return
            self.q.put(("model", MODEL))
            if not self.model_shown:
                self.model_shown = True
                self.q.put(("msg", f"Модель: {MODEL}" + (" (есть встроенное размышление)" if THINKS else ""), "sys"))
            files = self.cfg.get("files", [])
            if files:   # с прикреплёнными файлами: разбор файлов (в агенте или в чате)
                blob, imgs, notes_f = load_attachments(files, VISION)
                for n in notes_f:
                    self.q.put(("msg", n, "sys"))
                if self.cfg["agent"]:
                    self.agent(text, blob)
                else:
                    self.q.put(("status", "читаю файлы и отвечаю..."))
                    self.chat_answer(extra=blob, images=imgs or None)
                return
            steps = local_plan(text)
            tl = text.lower()
            messenger = re.search(r"телеграм|telegram|сообщени|в тг|контакт|@[a-z]\w{4,}", tl) or (
                re.search(r"(откро|запусти)\w*\s.*(напиши|напечатай)", tl) and not re.search(r"файл|код|скрипт|программ|игр|змейк|проект|функци", tl))
            if self.cfg["agent"] and not messenger and not (steps and all(s["action"] in PC_ACTIONS for s in steps)):
                self.agent(text)
                return
            is_q = ("?" in text or text.lower().split()[0] in QUESTION_WORDS) and not (
                messenger and re.match(r"\s*(откро|запусти|напиши|отправь|скинь|пошли)", tl))
            if steps is None:
                if not is_q and any(w in text.lower() for w in GATE):
                    self.q.put(("status", "определяю, что нужно..."))
                    steps = self.validate(route(self.history, self.last["name"] if self.last else None), text)
                else:
                    steps = [{"action": "chat", "arg": ""}]
            notes = []
            for s in steps:   # получатель берётся из @имени в твоём сообщении; текст при необходимости придумывает модель
                if s["action"] != "telegram_message":
                    continue
                rec, txt = split_msg(s["arg"])
                handle = re.search(r"@([A-Za-z][A-Za-z0-9_]{4,31})", text)
                if handle:
                    rec = "@" + handle.group(1)
                if txt.upper() == "AUTO" or (not txt and re.search(r"сам|придумай|что думаешь|что хочешь|любое|на свой вкус", tl)):
                    self.q.put(("status", "придумываю сообщение..."))
                    txt = complete(MODEL, [{"role": "system", "content": "Write one short friendly message in Russian (1-2 sentences) for a chat "
                                            "with a friend. Output only the message text, no quotes."},
                                           {"role": "user", "content": text}], self.stop, 0.7, 120, think=False).strip().strip('"«»')
                    if self.stop.is_set():
                        return
                s["arg"] = f"{rec} | {txt}"
                if not (rec and txt):
                    self.q.put(("msg", "Не понял, кому и что написать. Напиши, например: «напиши Васе в телеграм привет» или «напиши @username в телеграм привет».", "sys"))
                    return
            for k, s in enumerate(steps):   # печатать можно только сразу после открытия программы: проверяем до вопроса
                if s["action"] == "type_text" and (k == 0 or steps[k - 1]["action"] != "open_app"):
                    self.q.put(("msg", "Печатаю только сразу после открытия программы (например: «открой блокнот и напиши привет»).", "sys"))
                    return
            if any(s["action"] in ("type_text", "telegram_message") for s in steps):
                # подтверждаем ДО запуска: окно подтверждения забирает фокус, и после него печать попала бы не туда
                if not self.confirm(describe_plan(steps)):
                    self.q.put(("msg", "Отменено.", "sys"))
                    return
            prev = None
            for s in steps:
                if self.stop.is_set():
                    break
                action, arg = s["action"], s["arg"]
                if action == "chat":
                    self.q.put(("status", "отвечаю..."))
                    self.chat_answer()
                elif action == "write_code":
                    self.q.put(("status", "пишу код (на процессоре это может занять несколько минут)..."))
                    notes.append(self.make_code(arg))
                elif action == "read_file":
                    res, err = read_text(arg)
                    if res is None:
                        self.q.put(("msg", err, "sys"))
                        notes.append(err)
                    else:
                        self.q.put(("status", "читаю файл и отвечаю..."))
                        self.chat_answer(extra=f"File {res[0]}:\n```\n{res[1]}\n```")
                elif action in ("type_text", "telegram_message"):
                    if action == "type_text" and prev != "open_app":
                        ok, msg = False, "Печатаю только сразу после открытия программы (например: «открой блокнот и напиши привет»)."
                    elif action == "type_text":
                        ok, msg = self.type_into_active(arg)
                    else:
                        self.q.put(("status", "пишу в Telegram, не трогай мышь и клавиатуру..."))
                        ok, msg = self.telegram_send(arg)
                    self.q.put(("msg", msg, "ai" if ok else "sys"))
                    notes.append(msg)
                else:
                    ok, msg = run_action(action, arg, self.confirm)
                    self.q.put(("msg", msg, "ai" if ok else "sys"))
                    notes.append(msg)
                prev = action
            if notes:
                self.history.append({"role": "assistant", "content": " ".join(notes)})
        except Exception as e:
            self.q.put(("msg", f"Ошибка: {e}", "sys"))
        finally:
            self.save()
            self.q.put(("done",))

    def poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "msg":
                    self.say(item[1], item[2])
                elif item[0] == "stream":
                    self.put(item[1], item[2])
                elif item[0] == "clip":
                    self.root.clipboard_clear()
                    self.root.clipboard_append(item[1])
                    item[2].set()
                elif item[0] == "model":
                    self.model_box.set(item[1])
                elif item[0] == "status":
                    self.status.config(text=item[1])
                elif item[0] == "confirm":
                    item[3]["ok"] = messagebox.askyesno("Подтверждение", item[1])
                    item[2].set()
                elif item[0] == "done":
                    self.busy = False
                    self.stop_btn.config(state="disabled")
                    self.status.config(text="")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)


if __name__ == "__main__":
    root = TkinterDnD.Tk() if TkinterDnD else tk.Tk()
    App(root)
    root.mainloop()
