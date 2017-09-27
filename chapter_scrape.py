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


def append_section(Sections, chapter_section, section_title):
    section = {"chapter": chapter_section[0],
               "section": chapter_section[1],
               "name": section_title}
    Sections.append(section)
    section_title = ""
    chapter_section = ""


def main():
    baseURL = 'http://www.capitol.hawaii.gov/hrscurrent/Vol13_Ch0601-0676/HRS0601/HRS_0601-.htm'
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    Chapter = {"number": 205, "name": "Land Use Comission", "repealed": False}
    Sections = []

    # Prep the data by taking out the chapter title in bold
    bold_titles = soup .find_all('b')
    for bold_title in bold_titles:

        if "REPEALED" in bold_title.get_text():
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

            multiples = curr_section_title.split(' ')
            if multiples[0] == ',':
                # get the next section and make it REPEALED
                # and append it
                print("found a comma")
            elif multiples[0] == 'to':
                # get the next sections and make them REPEALED
                # and append it
                print("found a to")

        elif checkText(clean_line):
            curr_section_title += " " + clean_line

    if curr_section_title != "" and curr_chapter_section != "":
        append_section(Sections, curr_chapter_section,
                       curr_section_title)
    elif "REPEALED" in curr_section_title:
        Chapter['repealed'] = curr_section_title

    Chapter["sections"] = Sections
    outfile = open('chapter_example.json', 'w')
    json.dump(Chapter, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into chapter_example.json")


if __name__ == '__main__':
    main()
