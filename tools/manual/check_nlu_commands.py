"""Manually inspect NLU outputs for a small set of Arabic and English commands.

Run from the repository root:
    python -m tools.manual.check_nlu_commands
"""

from nlu import understand


TEST_COMMANDS = [
    "افتح Chrome",
    "open chrome",
    "افتح كروم",
    "open chorme",
    "شغل فايرفوكس",
    "اقفل Chrome",
    "اضبط الصوت على 70",
    "خلي الصوت 50",
    "اضبط الصوت",
    "delete report.pdf",
    "احذف test.txt",
    "اعرض الملفات",
    "اعرض الملفات في المستندات",
    "خذ سكرين شوت",
    "كم الساعة",
    "restart",
    "hello something random",
    "volume  100 خلي ",
    "ايد ال صوت",
    "ariana ",
    "خلي الصوت علي 40",
]


def main() -> None:
    for command in TEST_COMMANDS:
        print(f"\nINPUT: {command}")
        print("OUTPUT:")
        print(understand(command))


if __name__ == "__main__":
    main()
