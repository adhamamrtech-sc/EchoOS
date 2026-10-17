
"""Command catalog: the single source of truth for the NLU."""
 
from dataclasses import dataclass
from typing import Optional
 
from .normalize import normalize
 
 
# ============================================================
# APPLICATIONS
# ============================================================
 
APPS = {
    "chrome": [
        "chrome",
        "google chrome",
        "كروم",
        "الكروم",
        "جوجل كروم",
    ],
    "firefox": [
        "firefox",
        "فايرفوكس",
        "فاير فوكس",
        "الفايرفوكس",
    ],
    "vscode": [
        "vs code",
        "vscode",
        "visual studio code",
        "في اس كود",

    ],
    "terminal": [
        "terminal",
        "cmd",
        "تيرمنال",
        "ترمينال",
        "الترمينال",
        "الطرفية",
    ],
    "spotify": [
        "spotify",
        "سبوتيفاي",
    ],
    "vlc": [
        "vlc",
        "في ال سي",
    ],
    "calculator": [
        "calculator",
        "calc",
        "الاله الحاسبه",
        "الآلة الحاسبة",
    ],
    "files": [
        "files",
        "file manager",
        "مدير الملفات",
    ],
    "settings": [
        "settings",
        "الاعدادات",
    ],
}
 
 
# ============================================================
# FOLDERS
# ============================================================
 
FOLDERS = {
    "documents": [
        "documents",
        "docs",
        "المستندات",
        "مستندات",
    ],
    "downloads": [
        "downloads",
        "التنزيلات",
        "التحميلات",
        "تنزيلات",
        "تحميلات",
    ],
    "desktop": [
        "desktop",
        "سطح المكتب",
    ],
    "pictures": [
        "pictures",
        "الصور",
    ],
}
 
 
# ============================================================
# SYSTEM METRICS (for system_info)
# ============================================================
 
METRICS = {
    "cpu": [
        "cpu",
        "processor",
        "المعالج",
        "البروسيسور",
    ],
    "ram": [
        "ram",
        "memory",
        "الرام",
        "رام",
        "الذاكرة",
    ],
    "disk": [
        "disk",
        "storage",
        "hard disk",
        "القرص",
        "الهارد",
        "التخزين",
    ],
}
 
 
# ============================================================
# VERBS
# ============================================================
 
OPEN_VERBS = [
    normalize(verb)
    for verb in [
        "open",
        "launch",
        "start",
        "run",
        "افتح",
        "افتحلي",
        "فتح",
        "شغل",
        "اشغل",
        "شغلي",
        "ابدأ",
    ]
]
 
CLOSE_VERBS = [
    normalize(verb)
    for verb in [
        "close",
        "quit",
        "kill",
        "اقفل",
        "اقفلي",
        "اغلق",
        "سكر",
    ]
]
 
 
# ============================================================
# COMMAND
# ============================================================
 
@dataclass
class Command:
    action: str
    target: Optional[str]
    examples: list[str]
    keywords: list[str]
    needs: Optional[str] = None
    dangerous: bool = False
 
    @property
    def key(self) -> str:
        """Unique command identifier."""
        return f"{self.action}:{self.target}"
 
 
def make_command(
    action,
    target,
    examples,
    keywords,
    needs=None,
    dangerous=False,
) -> Command:
    """Create a normalized Command object."""
    return Command(
        action=action,
        target=target,
        examples=[normalize(example) for example in examples],
        keywords=[normalize(keyword) for keyword in keywords],
        needs=needs,
        dangerous=dangerous,
    )
 
 
# ============================================================
# STATIC COMMANDS
# ============================================================
 
STATIC_COMMANDS = [
    make_command(
        "open_app",
        "app",
        [
            "open chrome",
            "open firefox",
            "افتح كروم",
            "شغل فايرفوكس",
            "launch vscode",
        ],
        [
            "open",
            "launch",
            "start",
            "run",
            "افتح",
            "افتحلي",
            "اشغل",
            "شغل",
            "شغلي",
        ],
        needs="app",
    ),
    make_command(
        "close_app",
        "app",
        [
            "close chrome",
            "close firefox",
            "اقفل كروم",
            "اغلق فايرفوكس",
        ],
        [
            "close",
            "اقفل",
            "اقفلي",
            "اغلق",
        ],
        needs="app",
    ),
    make_command(
        "open_folder",
        "folder",
        [
            "open folder downloads",
            "open folder documents",
            "افتح فولدر التحميلات",
            "افتح مجلد المستندات",
        ],
        [
            "open folder",
            "افتح فولدر",
            "افتح مجلد",
        ],
        needs="folder",
    ),
    make_command(
        "shutdown",
        "system",
        [
            "shutdown",
            "shut down the computer",
            "power off",
            "اطفي الجهاز",
            "اغلق الكمبيوتر",
            "اقفل الجهاز",
        ],
        [
            "shutdown",
            "shut down",
            "power off",
            "اطفي الجهاز",
            "اطفئ الجهاز",
            "اغلق الجهاز",
            "اقفل الجهاز",
            "اغلق الكمبيوتر",
            "اقفل الكمبيوتر",
            "اطفي الكمبيوتر",
        ],
        dangerous=True,
    ),
    make_command(
        "restart",
        "system",
        [
            "restart",
            "restart the computer",
            "reboot",
            "اعد تشغيل الجهاز",
            "ريستارت",
        ],
        [
            "restart",
            "reboot",
            "اعادة تشغيل",
            "اعد تشغيل",
            "اعد التشغيل",
            "اعاده تشغيل",
            "ريستارت",
        ],
        dangerous=True,
    ),
    make_command(
        "screenshot",
        "screen",
        [
            "take a screenshot",
            "screenshot",
            "خذ لقطة شاشة",
            "سكرين شوت",
            "صور الشاشة",
        ],
        [
            "screenshot",
            "take screenshot",
            "screen shot",
            "لقطة شاشة",
            "لقطة الشاشة",
            "لقطه شاشه",
            "سكرين شوت",
            "سكرينشوت",
            "صور الشاشة",
            "صور الشاشه",
        ],
    ),
    make_command(
        "get_time",
        "system",
        [
            "what time is it",
            "what is the time",
            "tell me the time",
            "كم الساعة",
            "الساعة كام",
            "قولي الوقت",
        ],
        [
            "what time is it",
            "كم الساعة",
            "الساعة كام",
            "كام الساعة",
            "الوقت كام",
            "الوقت",
        ],
    ),
    make_command(
        "exit",
        "echoos",
        [
            "exit",
            "goodbye",
            "bye",
            "اخرج",
            "خروج",
            "مع السلامة",
        ],
        [
            "exit",
            "goodbye",
            "bye",
            "close assistant",
            "اخرج",
            "خروج",
            "انهاء",
            "وداعا",
            "مع السلامة",
        ],
    ),
    make_command(
        "set_volume",
        "system",
        [
            "set volume to 50",
            "change the volume to 30",
            "volume 70",
            "اضبط الصوت على 50",
            "خلي الصوت 80",
            "غير مستوى الصوت الى 40",
        ],
        [
            "set volume",
            "volume",
            "الصوت",
            "صوت",
            "فوليوم",
            "اضبط الصوت",
            "خلي الصوت",
            "علي الصوت",
            "وطي الصوت",
        ],
        needs="number",
    ),
    make_command(
        "delete_file",
        "file",
        [
            "delete report.pdf",
            "remove test.txt",
            "احذف الملف report.pdf",
            "امسح test.txt",
        ],
        [
            "delete",
            "remove",
            "احذف",
            "امسح",
            "حذف",
            "مسح",
        ],
        needs="filename",
        dangerous=True,
    ),
    make_command(
        "list_files",
        "files",
        [
            "list files",
            "show me the files",
            "list all files in documents",
            "اعرض الملفات",
            "اظهر لي الملفات",
            "اعرض الملفات في المستندات",
        ],
        [
            "list files",
            "show files",
            "show my files",
            "display files",
            "اعرض الملفات",
            "اظهر الملفات",
            "عرض الملفات",
            "اعرض لي الملفات",
        ],
    ),
    # ---------------- NEW COMMANDS ----------------
    make_command(
        "create_file",
        "file",
        [
            "create file notes.txt",
            "create a new file test.txt",
            "make file report.docx",
            "انشئ ملف notes.txt",
            "اعمل ملف test.txt",
        ],
        [
            "create file",
            "create a file",
            "create new file",
            "create a new file",
            "new file",
            "make file",
            "make a file",
            "انشئ ملف",
            "انشاء ملف",
            "انشي ملف",
            "اعمل ملف",
            "عمل ملف",
            "سوي ملف",
            "ملف جديد",
        ],
        needs="filename",
    ),
    make_command(
        "create_folder",
        "folder",
        [
            "create folder projects",
            "create a new folder my files",
            "make folder photos",
            "انشئ مجلد مشاريع",
            "اعمل فولدر صور",
        ],
        [
            "create folder",
            "create a folder",
            "create new folder",
            "create a new folder",
            "new folder",
            "make folder",
            "make a folder",
            "mkdir",
            "انشئ مجلد",
            "انشئ فولدر",
            "انشاء مجلد",
            "انشاء فولدر",
            "انشي مجلد",
            "انشي فولدر",
            "اعمل مجلد",
            "اعمل فولدر",
            "عمل مجلد",
            "عمل فولدر",
            "سوي مجلد",
            "سوي فولدر",
            "مجلد جديد",
            "فولدر جديد",
        ],
        needs="foldername",
    ),
    make_command(
        "rename_file",
        "file",
        [
            "rename old.txt to new.txt",
            "rename file a.pdf to b.pdf",
            "غير اسم الملف old.txt الى new.txt",
            "اعد تسمية الملف a.txt الى b.txt",
        ],
        [
            "rename file",
            "rename",
            "غير اسم الملف",
            "غير اسم",
            "اعادة تسمية الملف",
            "اعادة تسمية",
            "اعد تسمية الملف",
            "اعد تسمية",
        ],
        needs="rename",
    ),
    make_command(
        "show_processes",
        "system",
        [
            "show processes",
            "list running processes",
            "show running processes",
            "اعرض العمليات",
            "اظهر العمليات الشغالة",
        ],
        [
            "show processes",
            "list processes",
            "running processes",
            "processes",
            "اعرض العمليات",
            "اظهر العمليات",
            "عرض العمليات",
            "العمليات",
        ],
    ),
    make_command(
        "system_info",
        "system",
        [
            "show cpu usage",
            "show ram usage",
            "show disk usage",
            "system info",
            "how much memory is used",
            "اعرض استخدام المعالج",
            "معلومات النظام",
            "كام استخدام الرام",
        ],
        [
            "system info",
            "system usage",
            "system resources",
            "memory usage",
            "disk usage",
            "cpu usage",
            "cpu",
            "ram",
            "معلومات النظام",
            "موارد النظام",
            "استخدام المعالج",
            "استخدام الذاكرة",
            "استخدام الرام",
            "استخدام القرص",
            "المعالج",
            "الرام",
        ],
    ),
]
 
 
# ============================================================
# APP / FOLDER EXAMPLES FOR FUZZY + SEMANTIC
# ============================================================
 
def build_app_examples() -> list[tuple[Command, str]]:
    """Attach extra bilingual examples to open/close app commands."""
    open_command = next(command for command in STATIC_COMMANDS if command.action == "open_app")
    close_command = next(command for command in STATIC_COMMANDS if command.action == "close_app")
    extra = []
 
    open_verbs = ["open", "افتح", "شغل"]
    close_verbs = ["close", "اقفل", "اغلق"]
 
    for aliases in APPS.values():
        for alias in aliases:
            for verb in open_verbs:
                extra.append((open_command, normalize(f"{verb} {alias}")))
            for verb in close_verbs:
                extra.append((close_command, normalize(f"{verb} {alias}")))
 
    return extra
 
 
COMMANDS = STATIC_COMMANDS
 
COMMAND_BY_KEY = {
    command.key: command
    for command in COMMANDS
}
 
COMMAND_BY_ACTION = {
    command.action: command
    for command in COMMANDS
}
 
 
# Longest keywords first so "open folder" wins over "open",
# and "اقفل الجهاز" wins over "اقفل".
KEYWORDS = sorted(
    (
        (keyword, command)
        for command in STATIC_COMMANDS
        for keyword in command.keywords
        if keyword
    ),
    key=lambda pair: -len(pair[0]),
)
 
 
# ============================================================
# EXAMPLE INDEX
# ============================================================
 
SAFE_COMMANDS = [
    command
    for command in COMMANDS
    if not command.dangerous
]
 
EXAMPLE_TEXTS = []
EXAMPLE_OWNERS = []
 
seen_examples = set()
 
for command in SAFE_COMMANDS:
    for example in command.examples:
        if example and example not in seen_examples:
            seen_examples.add(example)
            EXAMPLE_TEXTS.append(example)
            EXAMPLE_OWNERS.append(command)
 
for command, example in build_app_examples():
    if example and example not in seen_examples:
        seen_examples.add(example)
        EXAMPLE_TEXTS.append(example)
        EXAMPLE_OWNERS.append(command)
