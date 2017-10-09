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


def checkMultiples(Sections, curr_chapter_section, curr_section_name):
    """ Checks a line for multiple statutes and appends to Sections """
    found_multiples = False
    chapter = curr_chapter_section[0]
    section = curr_chapter_section[1]

    multiples = curr_section_name.split(' ')

    # Ex. 16, 20
    if multiples[0] == ',':
        try:

            second_section = float(multiples[1])
            second_section = floatstrip(second_section)

            appendSection(Sections, [chapter, section], 'Repealed', None)
            appendSection(
                Sections, [chapter, second_section], 'Repealed', None)

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " multiple (,) contains a ValueError.")
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
                        Sections, [chapter, floatstrip(curr_section)], 'Repealed', None)
                    curr_section += increment

            found_multiples = True

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " multiple (to) contains a ValueError.")

    return found_multiples


def appendSection(Sections, chapter_section, section_name, url):
    """ Appends a section to a parent Section list """
    if url is not None:
        text = getSectionTextData(url, chapter_section[1])
        if text is not None:
            section = {"number": chapter_section[1],
                       "name": section_name,
                       "text": text}
            Sections.append(section)
        else:
            print("Error parsing text for: " +
                  (chapter_section[0]) + '-' + chapter_section[1])
    else:
        section = {"number": chapter_section[1],
                   "name": section_name,
                   "text": None}
        Sections.append(section)


def getSectionTextData(url, section):
    """ Preps the data by getting rid of bolded text """
    text_data = None
    section_url = None

    if '.' in section:
        # Check for articles with digits ex. 490:1-1.5
        if '-' in section:
            article_split = section.split('-')
            split_digit = article_split[1].split('.')

            # Check if there is a letter
            if re.search('[a-zA-Z]', article_split[0]):
                section_url = str(article_split[0]).zfill(
                    5) + '-' + str(split_digit[0]).zfill(4) + '_' + str(split_digit[1]).zfill(4) + '.htm'
            else:
                section_url = str(article_split[0]).zfill(
                    4) + '-' + str(split_digit[0]).zfill(4) + '_' + str(split_digit[1]).zfill(4) + '.htm'
        else:
            split_digit = section.split('.')
            section_url = str(split_digit[0]).zfill(
                    4) + "_" + str(split_digit[1]).zfill(4) + '.htm'
    else:
        # Check for articles
        if '-' in section:
            article_split = section.split('-')

            if re.search('[a-zA-Z]', article_split[0]):
                section_url = article_split[0].zfill(
                    5) + '-' + article_split[1].zfill(4) + '.htm'
            else:
                section_url = article_split[0].zfill(
                    4) + '-' + article_split[1].zfill(4) + '.htm'
        else:
            section_url = section.zfill(4) + '.htm'

    baseURL = url.replace('.htm', section_url)
    try:
        htmlToParse = requests.get(baseURL)
        soup = bs(htmlToParse.text, 'lxml')
        text_data = soup.find(
            'div', {'class': 'WordSection1'})
    except:
        print("Connection possibly timed out on: " + url)
        text_data = None
    if text_data is not None:
        text_data = text_data.get_text().replace('\r\n', ' ')
    return text_data


def prepSectionNameData(url):
    """ Preps the data by getting rid of bolded text """
    baseURL = url
    try:
        htmlToParse = requests.get(baseURL)
        soup = bs(htmlToParse.text, 'lxml')
    except:
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

    return soup.find_all('p', {'class': 'RegularParagraphs'})


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
                appendSection(Sections, curr_chapter_section,
                              curr_section_name, url)

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
        elif checkText(clean_line):
            curr_section_name += " " + clean_line

    # Check for anything left in the buffer
    if curr_section_name != "" and curr_chapter_section != "":
        appendSection(Sections, curr_chapter_section,
                      curr_section_name, url)

    # If nothing was scraped then the whoel chapter was actually repealed
    elif "REPEALED" in curr_section_name:
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
