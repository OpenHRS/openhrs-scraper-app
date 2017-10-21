import json
import requests
import re
import sys
import math
from bs4 import BeautifulSoup as bs

no_text = False
version = None
VERSIONS = ['hrscurrent',
            'hrs2016',
            'hrs2015',
            'hrs2014',
            'hrs2013',
            'hrs2012',
            'hrs2011',
            'hrs2010',
            'hrs2009',
            'hrs2008',
            'hrs2007',
            'hrs2006',
            'hrs2005',
            'hrs2004',
            'hrs2003',
            'hrs2002']

if len(sys.argv) > 1:
    if sys.argv[1] == 'notext' and sys.argv[2] in VERSIONS:
        version = sys.argv[2]
        no_text = True
        print('Scraping ' + version + ' with no text')

    elif sys.argv[1] in VERSIONS:
        version = sys.argv[1]
        if len(sys.argv) > 2 and sys.argv[2] == 'notext':
            no_text = True
            print('Scraping ' + version + ' with no text')
        else:
            print('Scraping ' + version)

####################################
#
# Line Parsing Functions
#
####################################


def cleanText(line):
    """ Function that cleans up all known defects that may be in the html """
    clean_text = line.get_text().replace(u'\xa0', "").strip()
    clean_text = clean_text.replace('\r\n', ' ')
    clean_text = clean_text.replace(u'\u2011', '-')

    return clean_text


def cleanCommas(line):
    # Helper function in checkMultiples to remove multiple commas
    clean_text = line.replace(',', '')
    return clean_text


def checkText(line):
    """ Compares a line to see if there are any blacklisted words"""
    is_okay = True

    blacklist = ["CHAPTER", "Part", "Section"]

    rgx_check = re.search('([A-Z])\. +(\w+)', line)

    if rgx_check is not None:
        is_okay = False

    for word in blacklist:
        if word in line:
            is_okay = False
        elif line == "":
            is_okay = False

    if "REPEALED" in line:
        is_okay = True

    return is_okay


def floatstrip(x):
    """ Given a float will return if it is actually an integer eg. 16.0 -> 16 """
    if x == int(x):
        return str(int(x))
    else:
        return str(x)

####################################
#
# Multiple Line checking (to and ',')
#
####################################


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
        appendSection(Sections, [chapter, section], 'Repealed', None)
        repealedInCheckMultiples(Sections, chapter, multiples)
        found_multiples = True

    # Ex. 16.5 to 16.8 REPEALED
    elif multiples[0] == 'to':
        try:
            increment = 0

            # if the section has a hypen ie 5A-300, it will split and only get
            # the second part
            curr_section_list = section.split('-')
            if len(curr_section_list) == 1:
                curr_section = float(section)
                is_article = False
            elif len(curr_section_list) == 2:
                curr_section = float(curr_section_list[1])
                is_article = True
            target_section = float(multiples[1])

            # Check if the multiple sections will increment by 1 or .1
            if target_section - math.floor(target_section) == 0:
                increment = 1
            elif target_section - math.floor(target_section) > 0:
                increment = .1

            if increment != 0:
                while curr_section <= target_section:
                    if is_article:
                        article_section = curr_section_list[
                            0] + '-' + floatstrip(curr_section)
                        appendSection(
                            Sections, [chapter, article_section], 'Repealed', None)
                    else:
                        appendSection(Sections, [chapter, floatstrip(
                            curr_section)], 'Repealed', None)
                    curr_section += increment

            found_multiples = True

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " multiple (to) contains a ValueError.")

    return found_multiples


def repealedInCheckMultiples(Sections, chapter, multiList):
    # Ex HRS 27-12-0001 not showing in json file
    # because REPEALED is in a line with multiple commas and other section
    # names
    length = len(multiList) - 1
    for x in range(1, length):
        if re.search('[0-9\.]+', multiList[x]) is not None:
            new_section = float(multiList[x])
            new_section = floatstrip(new_section)
            appendSection(Sections, [chapter, new_section], 'Repealed', None)

####################################
#
# Section Scraping
#
####################################


def prepSectionNameData(url):
    """ Preps the data by getting rid of bolded text """
    baseURL = url
    try:
        html_to_parse = requests.get(baseURL)
        soup = bs(html_to_parse.text, 'lxml')
    except:
        html_to_parse = requests.get(baseURL)
        soup = bs(html_to_parse.text, 'lxml')

    # Prep the data by taking out the chapter title in bold
    bold_titles = soup.find_all('b')
    leftover_text = ""
    get_stuff = False
    for bold_title in bold_titles:
        if bold_title.get_text():
            if get_stuff is False:
                leftover_text = ""

            rgx_code = re.search(
                '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w+)|(\d+))',
                bold_title.get_text())

            if version in VERSIONS[-4:]:
                if rgx_code is None and get_stuff is False:
                    rgx_code = re.search('[\w ]*\d+\w*\.?', bold_title.get_text())
                    if rgx_code is not None:
                        leftover_text = bold_title

                if rgx_code is None and get_stuff is True:
                    rgx_code = re.search('.*$', bold_title.get_text())
                    if rgx_code is not None:
                        leftover_text.append(rgx_code.match)
                        bold_title = leftover_text
                        get_stuff = False

            if "REPEALED" in bold_title.get_text() or rgx_code is not None:
                continue

            bold_title.decompose()

    return soup.find_all('p') if version in VERSIONS[-4:] else soup.find_all('p', {'class': 'RegularParagraphs'})

def scrapeSectionNames(url):
    Sections = []
    url = url.replace('hrscurrent', version)
    line_data = prepSectionNameData(url)

    curr_section_name = ""
    curr_chapter_section = ""

    # Go through each line (<p> tags) and associate the data
    for line in line_data:
        clean_line = cleanText(line).strip()

        # Looks for statute code in Regex ex. 123-45.5
        rgx_code = re.search(
            '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w{1})|(\d+))',
            clean_line)

        if rgx_code is not None:
            # If theres something being tracked already then append it
            if curr_section_name != "" and curr_chapter_section != "":
                appendSection(Sections, curr_chapter_section,
                              curr_section_name, url)

            # If space does not separate chapter-section and section name
            # do something about it
            extra_text = re.search(
                '(\d+[A-Z]?-\d+(\.\d)?[A-Z]?)([A-Z]{1}[a-z]+$)',
                clean_line)
            if extra_text is not None:
                clean_line = clean_line.replace(
                    extra_text.group(1), extra_text.group(1) + ' ')

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
                endPunc = re.search('([;, ]*)$', curr_chapter_section[1])
                if endPunc is not None:
                    curr_chapter_section[1] = curr_chapter_section[1].replace(
                        endPunc.group(0), "")
                else:
                    curr_chapter_section[1] = curr_chapter_section[1][:-1]

            # Check if there are multiple statutes in a line
            found_multiples = checkMultiples(
                Sections, curr_chapter_section, curr_section_name)

            if found_multiples:
                curr_section_name = ""
                curr_chapter_section = ""

        # If there isnt a statute in the line then append to previous name
        elif checkText(clean_line):
            if wordCountSectionName(clean_line) < 20:
                curr_section_name += " " + clean_line

    # Check for anything left in the buffer
    if curr_section_name != "" and curr_chapter_section != "":
        appendSection(Sections, curr_chapter_section,
                      curr_section_name, url)

    # If nothing was scraped then the whoel chapter was actually repealed
    elif "REPEALED" in curr_section_name:
        Sections = None

    return Sections


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
        html_to_parse = requests.get(baseURL)
        soup = bs(html_to_parse.text, 'lxml')
        # text_data = soup.find(
        #     'div', {'class': 'WordSection1'})
        text_data = soup.find('body')
    except:
        print("Connection possibly timed out on: " + url)
        text_data = None
    if text_data is not None:
        hrefs = text_data.find_all('a')

        for href in hrefs:
            href.decompose()

        text_data = text_data.get_text().replace('\r\n', ' ').strip()

    return text_data


def appendSection(Sections, chapter_section, section_name, url):
    """ Appends a section to a parent Section list """
    if url is not None and not no_text:

        excess_text = re.search(
            "(\d+(\.\d)?[A-Z]?)([A-Z]{1}[a-z]+$)", chapter_section[1])

        if excess_text is not None:
            chapter_section[1] = chapter_section[1].replace(excess_text.group(3), '')

        text = getSectionTextData(url, chapter_section[1])
        section = {"number": chapter_section[1],
                   "name": section_name}
        if text is not None:
            if "Page Not Found" in text:
                print("Error 404 for: " +
                      (chapter_section[0]) + '-' + chapter_section[1])
            else:
                if ('§' + chapter_section[0] + u'\u2011' + chapter_section[1]) in text and section_name in text:
                    text = text.replace(section_name + '.' if section_name[-1] != '.' else section_name, '')
                    text = text.replace('§' + chapter_section[0] + u'\u2011' + chapter_section[1], '')
                elif ('§' + chapter_section[0] + '-' + chapter_section[1]) in text and section_name in text:
                    text = text.replace(section_name + '.' if section_name[-1] != '.' else section_name, '')
                    text = text.replace('§' + chapter_section[0] + '-' + chapter_section[1], '')
                else:
                    if section_name in text:
                        text = text.replace(section_name + '.' if section_name[-1] != '.' else section_name, '')

                    if ('§' + chapter_section[0] + u'\u2011' + chapter_section[1]) in text:
                        text = text.replace('§' + chapter_section[0] + u'\u2011' + chapter_section[1], '')
                    elif ('§' + chapter_section[0] + '-' + chapter_section[1]) in text:
                        text = text.replace('§' + chapter_section[0] + '-' + chapter_section[1], '')
                    elif (chapter_section[0] + u'\u2011' + chapter_section[1]) in text:
                        text = text.replace(chapter_section[0] + u'\u2011' + chapter_section[1], '')
                    elif (chapter_section[0] + '-' + chapter_section[1]) in text:
                        text = text.replace(chapter_section[0] + '-' + chapter_section[1], '')

                brackets = re.search('^\[\]', text)
                if brackets is not None:
                    text = text.replace(brackets.group(0), '')
                elif '[' in text and text.find('[') == 0 and ']' in text:
                    text = text[(text.find(']') + 1):]
                elif '[' in text and text.find('[') == 0 and u'\u00a0' in text:
                    text = text[(text.find(u'\u00a0') + 1):]

                text = text.strip()
                section['text'] = text
                Sections.append(section)

        else:
            print("Error parsing text for: " +
                  (chapter_section[0]) + '-' + chapter_section[1])

    else:
        section = {"number": chapter_section[1],
                   "name": section_name}

        if not no_text:
            section['text'] = None
            Sections.append(section)


def checkLine(currentLine):
    retVal = True
    blackList = ["Chapter", "Subtitle"]

    for word in blackList:
        if word in currentLine:
            retVal = False

    return retVal


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


def scrapeTableOfContents():
    baseURL = 'http://www.capitol.hawaii.gov/docs/HRS.htm'
    html_to_parse = requests.get(baseURL)
    soup = bs(html_to_parse.text, 'lxml')

    Divisions = []
    Titles = []
    Chapters = []

    current_division = {}
    current_title = {}
    current_chapter = {}
    chapter_trigger = 0

    contents = soup.find_all('p', {'class': 'MsoNormal'})

    for content in contents:
        currentLine = content.get_text().replace('\r\n ', "")
        if checkLine(currentLine):
            if "DIVISION" in currentLine:
                if len(Titles) > 0:
                    current_title["chapters"] = Chapters
                    Titles.append(current_title)

                    current_division["titles"] = Titles
                    Divisions.append(current_division)

                    current_division = {}
                    current_title = {}
                    current_chapter = {}
                    Titles = []
                    Chapters = []

                    current_division["name"] = currentLine
                else:
                    current_division["name"] = currentLine

            elif "TITLE" in currentLine:
                if len(Chapters) > 0:
                    current_title["chapters"] = Chapters
                    Titles.append(current_title)

                    current_title = {}
                    current_chapter = {}
                    Chapters = []

                    current_title["name"] = currentLine
                else:
                    current_title["name"] = currentLine
            else:
                if chapter_trigger == 0:
                    current_chapter["number"] = currentLine
                    current_chapter["text"] = ""
                    chapter_trigger = 1

                elif chapter_trigger == 1:
                    current_chapter["text"] = currentLine
                    chapterUrl = content.a['href']
                    Sections = scrapeSectionNames(chapterUrl)

                    if Sections is not None:
                        current_chapter['repealed'] = False
                        current_chapter['sections'] = Sections
                    else:
                        current_chapter['repealed'] = True

                    Chapters.append(current_chapter)
                    current_chapter = {}
                    chapter_trigger = 0

    current_title["chapters"] = Chapters
    Titles.append(current_title)

    current_division["titles"] = Titles
    Divisions.append(current_division)

    return Divisions


def main():
    Divisions = scrapeTableOfContents()

    file_name = 'output/' + version + '.json'
    if no_text:
        file_name = 'output/' + version + '_notext.json'

    outfile = open(file_name, 'w')
    json.dump(Divisions, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into " + file_name)


if __name__ == '__main__':
    main()
