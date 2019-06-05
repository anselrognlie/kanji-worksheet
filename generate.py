#!/usr/local/bin/python3

from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

BIN = ""

class KanjiRecord:
    def __init__(self, kanji, grade, kanken, english, readings):
        self.kanji = kanji
        self.grade = grade
        self.kanken = kanken
        self.english = english
        self.readings = readings

class WorksheetGenerator:
    def __init__(self, list, seed=None, prefix=None):
        import sys
        import copy
        self.output = None
        self.list = copy.copy(list)
        self.key = True
        self.seed = seed
        self.indexList = None
        self.prefix = prefix

    def _getKeyStyle(self):
        if self.key:
            return ""
        else:
            return "display: none;"

    def _shuffle(self):
        import random
        self.indexList = [x for x in range(len(self.list))]

        if self.seed is not None:
            if self.seed == 0:
                # don't reorder
                return
            else:
                # use the supplied seed
                random.seed(self.seed)
        else:
            # randomize with internal seed
            random.seed()

        # do the shuffle
        random.shuffle(self.indexList)

    def _getPrefixedName(self, rootName):
        if self.prefix is None:
            return rootName

        return f"{self.prefix}-{rootName}"

    def _prepareQuiz(self):
        self.key = False

        self._closeOutput()

        filename = self._getPrefixedName("quiz.html")

        self.output = open(filename, "w")

    def _prepareKey(self):
        self.key = True

        self._closeOutput()

        filename = self._getPrefixedName("key.html")

        self.output = open(filename, "w")

    def _closeOutput(self):
        if self.output is not None:
            self.output.close()
            self.output = None

    def _cleanup(self):
        self._closeOutput()

    def generate(self):

        self._shuffle()

        # prepare quiz file
        self._prepareQuiz()
        self._generateOneFile()

        #prepare key file
        self._prepareKey()
        self._generateOneFile()

        self._cleanup()

    def _generateOneFile(self):
        self.output.write("""
            <html>
            <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style type="text/css">
            <!--

            .kanji-table {
                font-size: 8px;
                xwidth: 85em;
                width: 8in;
            }

            .entry {
                float: left;
                page-break-inside: avoid;
            }

            .entry > div {
                float: left;
                box-sizing: border-box;
                height: 4em;
            }

            .question {
                border: solid .01em black;
            }

            .question > div {
                box-sizing: border-box;
                width: 8em;
                overflow: hidden;
                padding: .2em;
                text-align: right;
            }

            .reading {
                height: 2.5em;
            }

            .reading > .content {
                font-size: .8em;
            }

            .meaning {
                height: 1.5em;
            }

            .kanji {
                width: 4em;
                text-align: center;
                border: solid .01em black;
                xborder-left-width: 0;
            }

            .kanji > .content {
                font-size: 3em;
                %(keyStyle)s
            }

            }
            -->
            </style>
            </head>
            <body>
            <div class="kanji-table">
        """ % { "keyStyle": self._getKeyStyle() })

        for index in self.indexList:
            record = self.list[index]
            last = ","
            last = last.join(record.readings)
            self.output.write(f"""
                <div class="entry">
                <div class="question">
                <div class="reading">
                <div class="content">
                { last }
                </div>
                </div>
                <div class="meaning">
                { record.english }
                </div>
                </div>
                <div class="kanji">
                <span class="content">
                { record.kanji }
                </span>
                </div>
                </div>
            """)

        self.output.write("""
            </div>
            </body>
            </html>
        """)

REMAP_KK_INT = {"1":"1", "1.5":"2", "2":"3", "2.5":"4", "3":"5", "4":"6",
    "5":"7", "6":"8", "7":"9", "8":"10", "9":"11", "10":"12"}

REMAP_INT_KK = {"1":"1", "2":"1.5", "3":"2", "4":"2.5", "5":"3", "6":"4",
    "7":"5", "8":"6", "9":"7", "10":"8", "11":"9", "12":"10"}

def selectRecords(db, query):
    # split on commas to get individual grades
    # split those results on dash to get ranges
    # let S by treated as 7 for the purpose of range generation
    disjoint = query.split(",")
    expanded = []
    for i in range(len(disjoint)):
        d = disjoint[i]
        conjoint = d.split("-")
        if len(conjoint) == 2:
            lower = conjoint[0].lower()
            upper = conjoint[1].lower()

            # check whether this is a kanken grade
            isKanken = False
            if lower[0] == "k" or upper[0] == "k":
                isKanken = True

                # strip the kanken marker from either part of the range
                if lower[0] == "k":
                    lower = lower[1:]
                if upper[0] == "k":
                    upper = upper[1:]

            # handle S grade queries
            if not isKanken:
                if upper == "s":
                    upper = "7"
                if lower == "s":
                    lower = "7"
            else:
                # this is kanken, and there might be half values
                # kanken has 1.5 and 2.5
                # so remap 1.5=>2, 2=>3, 2.5=>4, 3=>5, 4=>6, etc
                upper = REMAP_KK_INT[upper]
                lower = REMAP_KK_INT[lower]

            # all characters are removed, so now treat as numbers
            upper = int(upper)
            lower = int(lower)

            # make sure the order is correct
            if upper < lower:
                lower, upper = upper, lower

            #print(f"lower: {lower}, upper: {upper}")

            if not isKanken:
                # special 7 to S mapping
                r = [("S" if x == 7 else str(x))
                    for x in range(lower, upper + 1)]
            else:
                # mark each expansion as kanken
                r = [f"k{REMAP_INT_KK[str(x)]}" for x in range(lower, upper + 1)]

            expanded.extend(r)
        else:
            expanded.append(d.lower())

    #print(expanded)

    result = set()

    for grade in expanded:
        batch = set(db.get(grade, []))
        result |= batch

    return list(result)

def addRecord(db, record):
    #print(db.keys())

    # always add the record to the grade listing
    grade = record.grade
    gradeList = db.get(grade)

    if gradeList == None :
        gradeList = []
        db[grade] = gradeList

    gradeList.append(record)

    #if it has a kanken value, update that list as well
    kk = record.kanken

    if kk is not None:
        kkKey = f"k{kk}"
        kkList = db.get(kkKey)

        if kkList == None:
            kkList = []
            db[kkKey] = kkList

        kkList.append(record)

def newEmptyDb():
    return {}

def loadDbFromCleanCsv():
    import csv
    KANJI_FILE = "joyo.csv"

    db = newEmptyDb()

    with open(KANJI_FILE) as csvFile:
        reader = csv.reader(csvFile)
        for row in reader:
            kanji = row[0]
            grade = row[1]
            kanken = row[2]
            english = row[3]
            reading = row[4]
            reading = reading.split(',')
            record = KanjiRecord(kanji, grade, kanken, english, reading)
            addRecord(db, record)

    return db;            

def usage():
    print(f"usage: {BIN} [-p prefix] -g <grade_level(1-6,S,k10-1)>")
    

def main(argv):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """

    import sys, getopt

    try:
        opts, args = getopt.getopt(argv, "hp:g:")
    except getopt.GetoptError:
        usage()
        return 1

    prefix = None
    grades = None

    for opt, arg in opts:
        #print(f"opt: {opt}, arg: {arg}")
        if opt == "-h":
            usage()
            return 0
        if opt == "-p":
            prefix = arg
        if opt == "-g":
            grades = arg

    if grades is None:
        usage()
        return 2

    db = loadDbFromCleanCsv()
    quiz = selectRecords(db, grades)
    gen = WorksheetGenerator(quiz, prefix=prefix)
    gen.generate()

    print(f"Generated {len(quiz)} questions.", file=sys.stderr)


if __name__ == '__main__':
    import sys, os
    BIN = os.path.basename(sys.argv[0])
    main(sys.argv[1:])
