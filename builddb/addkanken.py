#!/usr/local/bin/python3

class KanjiRecord:
    def __init__(self, kanji, grade, english, readings):
        self.kanji = kanji
        self.grade = grade
        self.english = english
        self.readings = readings
        self.kanken = None

class KanjiRecordKankenRater:
    def __init__(self, db, kk4, kk3, kk2_5):
        self.db = db
        self.kk4 = kk4
        self.kk3 = kk3
        self.kk2_5 = kk2_5

    def applyRating(self):
        # simple rating for grades 1 (10) through 6 (5)
        kanken = 10
        kyoiku = 1
        for kyoiku in range(1, 7):
            grade = self.db.get(str(kyoiku))
            for rec in grade:
                rec.kanken = str(kanken);
            kanken -= 1

        # now do the more complicated S kanji
        # check each record against each kanken list,
        # if not found it must be 2

        grade = self.db.get("S")
        for rec in grade:
            if rec.kanji in self.kk4:
                rec.kanken = "4"
            elif rec.kanji in self.kk3:
                rec.kanken = "3"
            elif rec.kanji in self.kk2_5:
                rec.kanken = "2.5"
            else:
                rec.kanken = "2"

def addRecord(db, record):
    grade = record.grade
    gradeList = db.get(grade)

    if gradeList == None :
        gradeList = []
        db[grade] = gradeList

    gradeList.append(record)

def loadDbFromCsv():
    import csv
    KANJI_FILE = "joyo-kanji.csv"

    db = {}

    with open(KANJI_FILE) as csvFile:
        reader = csv.reader(csvFile)
        for row in reader:
            kanji = row[1]
            grade = row[5]
            english = row[7]
            readings = row[8].split('\n')
            readings = readings[0].split('、')
            for i in range(len(readings)):
                reading = readings[i].split("[")[0]
                readings[i] = reading
            record = KanjiRecord(kanji, grade, english, readings)
            addRecord(db, record)

    return db;

def loadKankenList(level):
    import csv
    KANKEN_FILE = f"kanken-{level}.csv"

    db = set()

    with open(KANKEN_FILE) as csvFile:
        reader = csv.reader(csvFile)
        for row in reader:
            kanji = row[0]
            db.add(kanji)

    return db;

def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """

    import sys

    # grades = "1"
    # if len(sys.argv) >= 2:
    #     grades = sys.argv[1]

    db = loadDbFromCsv()

    kanken4 = loadKankenList("4")
    kanken3 = loadKankenList("3")
    kanken2_5 = loadKankenList("2.5")

    rater = KanjiRecordKankenRater(db, kanken4, kanken3, kanken2_5)
    rater.applyRating()

    # print all grade 1 kanji
    #gradeOne = db.get("1")
    #gradeSix = db.get("6")
    #gradeS = db.get("S")

    #print(gradeOne[0].kanken)
    #print(gradeSix[0].kanken)
    # for x in range(10):
    #     rec = gradeS[x]
    #     print(f"{rec.kanji}, {rec.kanken}")

    import csv
    writer = csv.writer(sys.stdout)

    for key, value in db.items():
        for rec in value:
            # filter the kanji to remove any footnote indicator (split on space)
            kanji = rec.kanji.split(" ")
            readings = ",".join(rec.readings)
            writer.writerow([kanji[0], rec.grade, rec.kanken, rec.english,
                readings])

if __name__ == '__main__':
    main()
