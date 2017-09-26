import json
import requests
from bs4 import BeautifulSoup as bs


def checkLine(currentLine):
    retVal = True
    blackList = ["Chapter", "Subtitle"]

    for word in blackList:
        if word in currentLine:
            retVal = False

    return retVal


def main():
    baseURL = 'http://www.capitol.hawaii.gov/docs/HRS.htm'
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    Divisions = []
    Titles = []
    Chapters = []

    currentDivision = {}
    currentTitle = {}
    currentChapter = {}
    chapterTrigger = 0

    contents = soup.find_all('p', {'class': 'MsoNormal'})

    for content in contents:
        currentLine = content.get_text().replace('\r\n ', "")
        if checkLine(currentLine):
            if "DIVISION" in currentLine:
                if len(Titles) > 0:
                    currentTitle["chapters"] = Chapters
                    Titles.append(currentTitle)

                    currentDivision["titles"] = Titles
                    Divisions.append(currentDivision)

                    currentDivision = {}
                    currentTitle = {}
                    currentChapter = {}
                    Titles = []
                    Chapters = []

                    currentDivision["name"] = currentLine
                else:
                    currentDivision["name"] = currentLine

            elif "TITLE" in currentLine:
                if len(Chapters) > 0:
                    currentTitle["chapters"] = Chapters
                    Titles.append(currentTitle)

                    currentTitle = {}
                    currentChapter = {}
                    Chapters = []

                    currentTitle["name"] = currentLine
                else:
                    currentTitle["name"] = currentLine
            else:
                if chapterTrigger == 0:
                    currentChapter["number"] = currentLine
                    currentChapter["text"] = ""
                    chapterTrigger = 1

                elif chapterTrigger == 1:
                    currentChapter["text"] = currentLine
                    Chapters.append(currentChapter)
                    currentChapter = {}
                    chapterTrigger = 0

    currentTitle["chapters"] = Chapters
    Titles.append(currentTitle)

    currentDivision["titles"] = Titles
    Divisions.append(currentDivision)

    outfile = open('hrsTree.json', 'w')
    json.dump(Divisions, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into hrsTree.json")


if __name__ == '__main__':
    main()
