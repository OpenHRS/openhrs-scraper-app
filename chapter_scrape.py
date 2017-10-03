import json
import requests
import re
from bs4 import BeautifulSoup as bs


def cleanText(line):
    """ Function that cleans up all known defects that may be in the html """
    clean_text = line.get_text().replace(u'\xa0', "").strip()
    clean_text = clean_text.replace('\r\n', ' ')
    clean_text = clean_text.replace(u'\u2011', '-')

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


def checkMultiples(Sections, curr_chapter_section, curr_section_title):
    """ Checks a line for multiple statutes and appends to Sections """
    found_multiples = False
    chapter = curr_chapter_section[0]
    section = curr_chapter_section[1]

    multiples = curr_section_title.split(' ')

    # Ex. 16, 20
    if multiples[0] == ',':
        try:

            second_section = float(multiples[1])
            second_section = floatstrip(second_section)

            append_section(Sections, [chapter, section], 'Repealed')
            append_section(Sections, [chapter, second_section], 'Repealed')

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
                    append_section(
                        Sections, [chapter, floatstrip(curr_section)], 'Repealed')
                    curr_section += increment

            found_multiples = True

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " may be broken")

    return found_multiples


def append_section(Sections, chapter_section, section_title):
    """ Appends a section to a parent Section list """
    section = {"chapter": chapter_section[0],
               "section": chapter_section[1],
               "name": section_title}
    Sections.append(section)


def scrapeSectionNames(url):
    baseURL = url
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    Sections = []

    # Prep the data by taking out the chapter title in bold
    bold_titles = soup .find_all('b')
    for bold_title in bold_titles:
        rgx_code = re.search(
            '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w+)|(\d+))',
            bold_title.get_text())

        if "REPEALED" in bold_title.get_text() or rgx_code is not None:
            continue

        bold_title.decompose()

    line_data = soup.find_all('p', {'class': 'RegularParagraphs'})

    curr_section_title = ""
    curr_chapter_section = ""

    # Go through each line (<p> tags) and associate the data
    for line in line_data:
        clean_line = cleanText(line)

        # Looks for statute code in Regex ex. 123-45.5
        rgx_code = re.search(
            '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w+)|(\d+))',
            clean_line)

        if rgx_code is not None:
            # If theres something being tracked already then append it
            if curr_section_title != "" and curr_chapter_section != "":
                append_section(Sections, curr_chapter_section,
                               curr_section_title)

            section_title = clean_line.replace(
                rgx_code.group(0), '')

            curr_section_title = section_title.strip()
            curr_chapter_section = rgx_code.group(0).split('-')

            found_multiples = checkMultiples(
                Sections, curr_chapter_section, curr_section_title)

            if found_multiples:
                curr_section_title = ""
                curr_chapter_section = ""

        elif checkText(clean_line):
            curr_section_title += " " + clean_line

    if curr_section_title != "" and curr_chapter_section != "":
        append_section(Sections, curr_chapter_section,
                       curr_section_title)
    elif "REPEALED" in curr_section_title:
        Sections = None

    return Sections


def main():
    Chapter = {"number": 205, "name": "Land Use Comission", "repealed": False}

    Sections = scrapeSectionNames(
        'http://www.capitol.hawaii.gov/hrs2016/Vol06_Ch0321-0344/HRS0321/HRS_0321-.htm')

    if Sections is None:
        Chapter['repealed'] = True
    else:
        Chapter["sections"] = Sections

    outfile = open('chapter_example.json', 'w')
    json.dump(Chapter, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into chapter_example.json")


if __name__ == '__main__':
    main()
