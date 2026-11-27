from nlu import understand


tests = [
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
    "create file notes.txt",
    "create folder projects",
    "rename old.txt to new.txt",
    "delete report.pdf",
    "show processes",
    "show ram and disk usage",

]


for text in tests:
    print(f"\nINPUT: {text}")
    result = understand(text)
    print("OUTPUT:")
    print(result)
