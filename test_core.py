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
    "ايد ال صوت",
    "ariana ",
    "خلي الصوت علي 40"

]


for text in tests:
    print(f"\nINPUT: {text}")
    result = understand(text)
    print("OUTPUT:")
    print(result)
