import json
import requests
import re
from bs4 import BeautifulSoup as bs


def checkText(text):
    is_okay = True

    blacklist = ["CHAPTER", "Part", "Section"]

    for word in blacklist:
        if word in text:
            is_okay = False
        elif text == "":
            is_okay = False

    return is_okay


def main():
    baseURL = 'http://www.capitol.hawaii.gov/hrscurrent/Vol04_Ch0201-0257/HRS0205/HRS_0205-.htm'
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    Chapter = {"number": 205, "name": "Land Use Comission"}

    bold_titles = soup .find_all('b')
    for bold_title in bold_titles:
        bold_title.decompose()

    raw_sections = soup.find_all('p', {'class': 'RegularParagraphs'})

    Sections = []

    curr_section_title = ""
    curr_chapter_section = ""
    for raw_section in raw_sections:
        clean_section = raw_section.get_text().replace(u'\xa0', "").strip()
        clean_section = clean_section.replace('\r\n', ' ')

        chapter_section_reg = re.search(
            '(\d+|\w+)\-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w+)|(\d+))',
            raw_section.text)

        if chapter_section_reg is not None:
            if curr_section_title != "" and curr_chapter_section != "":
                section = {"chapter": float(curr_chapter_section[0]),
                           "section": float(curr_chapter_section[1]),
                           "name": curr_section_title}
                Sections.append(section)
                curr_section_title = ""
                curr_chapter_section = ""

            section_title = clean_section.replace(
                chapter_section_reg.group(0) + ' ', '')

            curr_section_title = section_title
            curr_chapter_section = chapter_section_reg.group(0).split('-')

            #print(chapter + "-" + section + section_title)
        elif checkText(clean_section):
            curr_section_title += " " + clean_section

    Chapter["sections"] = Sections
    outfile = open('chapter_example.json', 'w')
    json.dump(Chapter, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into chapter_example.json")


if __name__ == '__main__':
    main()
