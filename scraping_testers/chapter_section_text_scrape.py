import json
import requests
import re
from bs4 import BeautifulSoup as bs

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
                  '-' + section + " may be broken")
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
                        Sections, floatstrip(curr_section), 'Repealed', None)
                    curr_section += increment
                    if increment == .1:
                        while re.search('\.[1-9]{2,}$', str(curr_section)) is not None:
                            curr_section = round(curr_section, 1)

            found_multiples = True

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " may be broken")

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
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    # Prep the data by taking out the chapter title in bold
    bold_titles = soup .find_all('b')
    for bold_title in bold_titles:
        rgx_code = re.search(
            '([\d\w]+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w{1})|(\d+))',
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
            '([\d\w]+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w{1})|(\d+))|(\d+\:\d+\w?-\d+\w?)',
            clean_line)

        if rgx_code is not None:
            # If theres something being tracked already then append it
            if curr_section_name != "" and curr_chapter_section != "":
                appendSection(Sections, curr_chapter_section,
                              curr_section_name, url)

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

            # If chapter-section has a colon
            secNumBegin1 = re.search('(^\d+\:)', curr_chapter_section[0])
            if secNumBegin1 is not None:
                frags = curr_chapter_section[0].split(':')
                curr_chapter_section[0] = frags[0]
                curr_chapter_section[1] = frags[1] + '-' + curr_chapter_section[1]

            # If the curr_chapter_section ends w/ a capital letter
            # and curr_section_name starts with a lowercase letter
            # and has stuff after it
            chapSecEnd = re.search('[A-Z]$', curr_chapter_section[1])
            secNameBegin = re.search('^[a-z]{3,}', curr_section_name)

            if chapSecEnd is not None and secNameBegin is not None:
                curr_section_name = curr_chapter_section[
                    1][-1] + curr_section_name
                curr_chapter_section[1] = curr_chapter_section[1][:-1]

            extra_letter = re.search('[A-Z]$', curr_chapter_section[1])

            if extra_letter is not None:
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


def main():
    Chapter = {"number": 412, "name": "UNIFORM CHILD-CUSTODY JURISDICTION AND ENFORCEMENT ACT", "repealed": False}
    url = 'http://www.capitol.hawaii.gov/hrscurrent/Vol08_Ch0401-0429/HRS0412/HRS_0412-.htm'
    Sections = scrapeSectionNames(url)

    if Sections is None:
        Chapter['repealed'] = True
    else:
        Chapter["sections"] = Sections

    outfile = open('output/section_text_example.json', 'w')
    json.dump(Chapter, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into section_text_example.json")


if __name__ == '__main__':
    main()
