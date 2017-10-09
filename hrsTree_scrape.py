import json
import requests
import re
from bs4 import BeautifulSoup as bs


def cleanText(line):
    """ Function that cleans up all known defects that may be in the html """
    clean_text = line.get_text().replace(u'\xa0', "").strip()
    clean_text = clean_text.replace('\r\n', ' ')
    clean_text = clean_text.replace(u'\u2011', '-')
    clean_text = clean_text.replace(u'\u00a7', '')

    return clean_text


def cleanCommas(line):
    # Helper function in checkMultiples to remove multiple commas
    clean_text = line.replace(',', '')
    return clean_text


def checkText(text):
    """ Compares a line to see if there are any blacklisted words"""
    is_okay = True

    blacklist = ["CHAPTER", "Part", "Section"]

    rgx_check = re.search('([A-Z])\. +(\w+)', text)

    if rgx_check is not None:
        is_okay = False

    for word in blacklist:
        if word in text:
            is_okay = False
        elif text == "":
            is_okay = False

    if "REPEALED" in text:
        is_okay = True

    return is_okay


def floatstrip(x):
    """ Given a float will return if it is actually an integer eg. 16.0 -> 16 """
    if x == int(x):
        return str(int(x))
    else:
        return str(x)


def repealedInCheckMultiples(Sections, multiList):
    # Ex HRS 27-12-0001 not showing in json file
    # because REPEALED is in a line with multiple commas and other section names
    length = len(multiList) - 1
    for x in range(1, length):
        new_section = float(multiList[x])
        new_section = floatstrip(new_section)
        appendSection(Sections, new_section, 'Repealed')


def checkMultiples(Sections, curr_chapter_section, curr_section_name):
    """ Checks a line for multiple statutes and appends to Sections """
    found_multiples = False
    chapter = curr_chapter_section[0]
    section = curr_chapter_section[1]

    multiples = curr_section_name.split(' ')
    # Ex. 16, 20
    # Making the assumption that multiple statutes on a line means they are
    # all REPEALED

    if multiples[0] == ',':
        multiples = cleanCommas(curr_section_name).split(' ')
        appendSection(Sections, section, 'Repealed')
        repealedInCheckMultiples(Sections, multiples)
        found_multiples = True

    # Ex. 16.5 to 16.8 REPEALED
    elif multiples[0] == 'to':
        try:
            increment = 0
            curr_section = float(section)
            target_section = float(multiples[1])

            # Check if the multiple sections will increment by 1 or .1
            if target_section % 1 == 0:
                increment = 1
            elif target_section % .1 == 0:
                increment = .1

            if increment != 0:
                while curr_section <= target_section:
                    appendSection(
                        Sections, floatstrip(curr_section), 'Repealed')
                    curr_section += increment

            found_multiples = True

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " multiple (to) contains a ValueError.")

    return found_multiples


def appendSection(Sections, section, section_name):
    """ Appends a section to a parent Section list """
    section = {"number": section,
               "name": section_name}
    Sections.append(section)


def prepSectionNameData(url):
    """ Preps the data by getting rid of bolded text """
    baseURL = url
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    # Prep the data by taking out the chapter title in bold
    bold_titles = soup .find_all('b')
    for bold_title in bold_titles:
        rgx_code = re.search(
            '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w+)|(\d+))',
            bold_title.get_text())

        if "REPEALED" in bold_title.get_text() or rgx_code is not None:
            continue

        bold_title.decompose()
        """ removes bold tag from text"""

    return soup.find_all('p', {'class': 'RegularParagraphs'})


def wordCountSectionName(line):
    # Because some miscellaneous info are also tagged as regular paragraphs, need a wordcount so that they don't
    # get added as a section name or appended to an existing one
    # Ex. HRS 84 number 43 and the tags the PREAMBLE is in
    # http://www.capitol.hawaii.gov/hrscurrent/Vol02_Ch0046-0115/HRS0084/HRS_0084-.htm
    words = line.split()
    count = 0
    for word in words:
        count += 1
    return count


def scrapeSectionNames(url):
    Sections = []

    line_data = prepSectionNameData(url)

    curr_section_name = ""
    curr_chapter_section = ""

    # Go through each line (<p> tags) and associate the data
    for line in line_data:
        clean_line = cleanText(line)

        # Looks for statute code in Regex ex. 123-45.5
        rgx_code = re.search(
            '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w{1})|(\d+))',
            clean_line)

        if rgx_code is not None:
            # If theres something being tracked already then append it
            if curr_section_name != "" and curr_chapter_section != "":
                appendSection(Sections, curr_chapter_section[1],
                              curr_section_name)

            # The section name is the currentline - the statute code
            curr_section_name = clean_line.replace(
                rgx_code.group(0), '').strip()
            curr_chapter_section = rgx_code.group(0).split('-')

            # If the section name begins with /\d+:/ delete it
            secNameBegin1 = re.search('(^\d+: )', curr_section_name)
            if secNameBegin1 is not None:
                curr_section_name = curr_section_name.replace(
                    secNameBegin1.group(0), "")
                curr_chapter_section[1] = curr_chapter_section[
                    0] + '-' + curr_chapter_section[1]

            # If the curr_chapter_section ends w/ a capital letter
            # and curr_section_name starts with a lowercase letter
            # and has stuff after it
            chapSecEnd = re.search('[A-Z]$', curr_chapter_section[1])
            secNameBegin = re.search('^[a-z].{3,}', curr_section_name)

            if chapSecEnd is not None and secNameBegin is not None:
                curr_section_name = curr_chapter_section[
                    1][-1] + curr_section_name
                curr_chapter_section[1] = curr_chapter_section[1][:-1]

            # Check if there are multiple statutes in a line
            found_multiples = checkMultiples(
                Sections, curr_chapter_section, curr_section_name)

            if found_multiples:
                curr_section_name = ""
                curr_chapter_section = ""

        # If there isnt a statute in the line then append to previous name
        # number can be changed if it causes bugs
        # if a section name is more than 10 words, it's probably not a section
        # name
        elif checkText(clean_line):
            if wordCountSectionName(clean_line) < 20:
                curr_section_name += " " + clean_line

    # Check for anything left in the buffer
    if curr_section_name != "" and curr_chapter_section != "":
        appendSection(Sections, curr_chapter_section[1],
                      curr_section_name)

    # If nothing was scraped then the whoel chapter was actually repealed
    if "REPEALED" in curr_section_name:
        Sections = None

    return Sections


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
                    chapterUrl = content.a['href']
                    Sections = scrapeSectionNames(chapterUrl)

                    if Sections is not None:
                        currentChapter['repealed'] = False
                        currentChapter['sections'] = Sections
                    else:
                        currentChapter['repealed'] = True

                    Chapters.append(currentChapter)
                    currentChapter = {}
                    chapterTrigger = 0

    currentTitle["chapters"] = Chapters
    Titles.append(currentTitle)

    currentDivision["titles"] = Titles
    Divisions.append(currentDivision)

    outfile = open('output/hrsTree.json', 'w')
    json.dump(Divisions, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into output/hrsTree.json")


if __name__ == '__main__':
    main()
