import json
import requests
import re
import sys
import math
import time
from bs4 import BeautifulSoup as BeauSoup

no_text = False
version = 'hrscurrent'
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
    else:
        print("No version was provided. Defaulting to hrscurrent")


""" Line parsing functions

These functions handle general line parsing
"""


def cleanup_text(line):
    """ Function that cleans up all known defects that may be in the html """
    clean_text = line.get_text().replace(u'\xa0', "").strip()
    clean_text = clean_text.replace('\r\n', ' ')
    clean_text = clean_text.replace(u'\u2011', '-')
    clean_text = clean_text.replace(u'\u00a7', '')
    clean_text = clean_text.strip(' \t\n\r')

    return clean_text


def clean_commas(line):
    # Helper function in check_multiples to remove multiple commas
    clean_text = line.replace(',', '')
    return clean_text


def check_text(line):
    """ Compares a line to see if there are any blacklisted words"""
    is_okay = True

    blacklist = ["CHAPTER", "Part", "Section"]

    rgx_check = re.search('([A-Z])\. +(\w+)', line)

    if rgx_check is not None:
        is_okay = False

    if line == "":
        is_okay = False
    else:
        for word in blacklist:
            if word in line:
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


""" Multiple line parsing functions

These functions handle lines on chapter pages that contain 'to' and ','

For example: '206E-151 to 159  Repealed' or '206E-151, 152  Repealed'
"""


def check_multiples(sections, curr_chapter_section, curr_section_name):
    """ Checks a line for multiple statutes and appends to Sections """
    found_multiples = False
    chapter = curr_chapter_section[0]
    section = curr_chapter_section[1]

    multiples = curr_section_name.split(' ')
    # Ex. 16, 20
    # Making the assumption that multiple statutes on a line means they are
    # all REPEALED

    if multiples[0] == ',':
        multiples = clean_commas(curr_section_name).split(' ')
        append_section(sections, [chapter, section], 'Repealed', None)
        repealed_in_check_multiples(sections, chapter, multiples)
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
                        append_section(
                            sections, [chapter, article_section], 'Repealed', None)
                    else:
                        append_section(sections, [chapter, floatstrip(
                            curr_section)], 'Repealed', None)
                    curr_section += increment
                    if increment == .1:
                        if re.search('\.\d{2,}$', str(curr_section)) is not None:
                            curr_section = round(curr_section, 1)

            found_multiples = True

        except ValueError:
            print("Chapter-section: " + chapter +
                  '-' + section + " multiple (to) contains a ValueError.")

    return found_multiples


def repealed_in_check_multiples(sections, chapter, multilist):
    # Ex HRS 27-12-0001 not showing in json file
    # because REPEALED is in a line with multiple commas and other section
    # names
    length = len(multilist) - 1
    for x in range(1, length):
        if re.search('^\d+(\.\d+)?$', multilist[x]) is not None:
            new_section = float(multilist[x])
            new_section = floatstrip(new_section)
            append_section(sections, [chapter, new_section], 'Repealed', None)


""" Section scraping functions

These functions handle individual section scraping and their dependencies

Functions gather information from the HRS table of contents given
by http://www.capitol.hawaii.gov/docs/HRS.htm and append appropriate section
data in a tree format by Division Title and Chapter.
"""


def prep_section_name_data(url):
    """ Preps the data by getting rid of bolded text """
    base_url = url

    html_to_parse = ''

    while html_to_parse == '':
        try:
            html_to_parse = requests.get(base_url)

            if html_to_parse.status_code == 200:
                soup = BeauSoup(html_to_parse.text, 'lxml')

                # Prep the data by taking out the chapter title in bold
                bold_titles = soup.find_all('b')
                leftover_text = ""
                get_stuff = False
                for bold_title in bold_titles:
                    if bold_title.get_text():
                        if get_stuff is False:
                            leftover_text = ""

                        if "REPEALED" in bold_title.get_text():
                            continue

                        bold_title.decompose()

                if version in VERSIONS[-4:]:
                    return soup.find_all('p')
                else:
                    return soup.find_all('p', {'class': 'RegularParagraphs'})

            elif html_to_parse.status_code == 404:
                stat_code = 404
                break
        except:
            continue
    else:
        return -1


def scrape_section_names(url):
    sections = []
    url = url.replace('hrscurrent', version)
    valid = requests.get(url)

    # Validate URL. If 404, get similar URL.
    if valid.status_code == 404:
        toc = requests.get('http://www.capitol.hawaii.gov/' + version)

        soup = BeauSoup(toc.text, 'lxml')
        links = soup.find_all('a')
        url_should_be_ok = False
        for link in links:
            if not url_should_be_ok:
                href = link['href']
                if href != '/':
                    split_href = href.split("/")
                    split_url = url.split("/")
                    href_extr = split_href[2]
                    url_extr = split_url[4]
                    if href_extr.split("_")[0] == url_extr.split("_")[0]:
                        url = url.replace(url_extr, href_extr)
                        url_should_be_ok = True

    line_data = -1
    while line_data == -1:
        line_data = prep_section_name_data(url)

    curr_section_name = ""
    curr_chapter_section = ""

    # Go through each line (<p> tags) and associate the data
    if line_data is not None:
        for line in line_data:
            clean_line = cleanup_text(line).strip()

            # Looks for statute code in Regex ex. 123-45.5
            rgx_code = re.search(
                '(\d:)?(\d+\w?)-((\d+\.)?(\d+\w?)?)', clean_line)

            if rgx_code is not None:
                # If something is being tracked already, append it
                if curr_section_name != "" and curr_chapter_section != "":
                    append_section(sections, curr_chapter_section,
                                   curr_section_name, url)

                # The section name is the current line - the statute code
                curr_section_name = clean_line.replace(
                    rgx_code.group(0), '').strip()
                curr_chapter_section = rgx_code.group(0).split('-')

                # If space does not separate chapter-section and section name
                # do something about it
                extra_text = re.search(
                    '(\d+[A-Z]?-\d+(\.\d)?[A-Z]?)([A-Z][a-z]+$)',
                    clean_line)
                if extra_text is not None:
                    clean_line = clean_line.replace(
                        extra_text.group(1), extra_text.group(1) + ' ')


                # If the section name begins with /\d+ / delete it
                sec_name_begin_1 = re.search('(^\d+ )', curr_section_name)
                if sec_name_begin_1 is not None:
                    curr_section_name = curr_section_name.replace(
                        sec_name_begin_1.group(0), "")

                # If chapter-section has a colon
                sec_num_begin_1 = re.search('(^\d+:)', curr_chapter_section[0])
                if sec_num_begin_1 is not None:
                    frags = curr_chapter_section[0].split(':')
                    curr_chapter_section[0] = frags[0]
                    curr_chapter_section[1] = frags[
                        1] + '-' + curr_chapter_section[1]

                # If the curr_chapter_section ends w/ a capital letter
                # and curr_section_name starts with a lowercase letter
                # and has stuff after it
                chap_sec_end = re.search('[A-Z]$', curr_chapter_section[1])
                sec_name_begin = re.search('^[a-z]{3,}', curr_section_name)

                if chap_sec_end is not None and sec_name_begin is not None:
                    curr_section_name = curr_chapter_section[
                        1][-1] + curr_section_name
                    end_punc = re.search('([;, ]*)$', curr_chapter_section[1])
                    if end_punc is not None:
                        curr_chapter_section[1] = curr_chapter_section[
                            1].replace(end_punc.group(0), "")
                    else:
                        curr_chapter_section[1] = curr_chapter_section[1][:-1]

                extra_letter = re.search('[A-Z]$', curr_chapter_section[1])

                if extra_letter is not None:
                    curr_chapter_section[1] = curr_chapter_section[1][:-1]

                # Check if there are multiple statutes in a line
                found_multiples = check_multiples(
                    sections, curr_chapter_section, curr_section_name)

                if found_multiples:
                    curr_section_name = ""
                    curr_chapter_section = ""

            # If there is no statute in the line, append to previous name
            elif check_text(clean_line):
                if word_count_section_name(clean_line) < 20:
                    curr_section_name += " " + clean_line

    # Check for anything left in the buffer
    if curr_section_name != "" and curr_chapter_section != "":
        append_section(sections, curr_chapter_section, curr_section_name, url)

    # If nothing was scraped then the whole chapter was actually repealed
    elif "REPEALED" in curr_section_name:
        sections = None

    return sections


def create_article_url(section):
    """ Helper function to create_section_url
    :param section: section string containing article ex. 3-506.5
    :return: String of url to section
    """
    article_url = None
    article_split = section.split('-')
    digit_split = article_split[1].split('.')

    # Special case where letters need a zfill of 5
    if re.search('[a-zA-Z]', article_split[0]):
        section_a = article_split[0].zfill(5)
    else:
        section_a = article_split[0].zfill(4)

    # Check if there is a digit
    if len(digit_split) > 1:
        section_b = digit_split[0].zfill(4)
        section_digit = digit_split[1].zfill(4)
        article_url = section_a + '-' + section_b + '_' + section_digit + '.htm'
    else:
        section_b = article_split[1].zfill(4)
        article_url = section_a + '-' + section_b + '.htm'

    return article_url


def create_section_url(base_url, section):
    """ Helper function to get_section_text_data
    :param base_url: The base chapter URL
    :param section: The section number ex. 105, 105D, 105.5
    :return: String of url to section
    """

    section_url = None
    section = str(section)

    # Check for Articles
    if '-' in section:
        section_url = create_article_url(section)

    elif '.' in section:
        split_digit = section.split('.')
        section_url = split_digit[0].zfill(
            4) + "_" + split_digit[1].zfill(4) + '.htm'
    else:
        section_url = section.zfill(4) + '.htm'

    section_url = base_url.replace('.htm', section_url)
    return section_url


def get_section_text_data(url, section):
    """ Driver function that gathers section text
    :param url: The base chapter URL
    :param section: The section number ex. 105, 105D, 105.5
    :return: The text for a given section number.
    """

    text_data = None
    section_url = create_section_url(url, section)

    good = True
    found = True

    while text_data is None and found:
        try:
            html_to_parse = requests.get(section_url)
            if html_to_parse.status_code == 404:
                found = False
                print(section_url + " not found.")
            elif html_to_parse.status_code == 200:
                soup = BeauSoup(html_to_parse.text, 'lxml')
                if good is False:
                    print("Reconnection to " + section_url + ". SUCCESSFUL...")
                    good = True
                text_data = soup.find('body')
        except:
            # Reconnect on connection timeout
            time.sleep(.4625)
            print("Connection timeout on: " +
                  section_url + ". RECONNECTING...")
            good = False
            text_data = None

    if text_data is not None:
        text_data = text_data.get_text().replace('\r\n', ' ').strip()

    return text_data


def append_section(sections, chapter_section, section_name, url):
    section = {"number": chapter_section[1],
               "name": section_name}

    text = None

    """ Appends a section to a parent Section list """
    if url is not None and not no_text:

        # Check for excess text in section number string...
        excess_text = re.search(
            "(\d+(\.\d)?[A-Z]?)([A-Z][a-z]+$)", chapter_section[1])

        # ... and delete excess text if it exists
        if excess_text is not None:
            chapter_section[1] = chapter_section[
                1].replace(excess_text.group(3), '')

        text = get_section_text_data(url, chapter_section[1])

        if text is not None:
            # The code explains everything.
            sec_sym = re.search('\[?§' + chapter_section[0] + "." + chapter_section[1] + "\]?", text)

            if sec_sym is not None:
                text = text.replace(sec_sym.group(0), '')

            if section_name in text:
                text = text.replace(
                    section_name + '.' if section_name[-1] != '.' else section_name, '')

            text = text.strip()

            brackets = re.search("^\[.*\]", text)
            if brackets is not None:
                text = text.replace(brackets.group(0), '')

            text = text.strip()

            brackets = re.search("^]", text)
            if brackets is not None:
                text = text.replace(brackets.group(0), '')

            text = text.strip()

        else:
            print("Error parsing text for: " +
                  (chapter_section[0]) + '-' + chapter_section[1])

    section['text'] = text

    sections.append(section)


def check_line(current_line):
    return_val = True
    blacklist = ["Chapter", "Subtitle"]

    for word in blacklist:
        if word in current_line:
            return_val = False

    return return_val


def word_count_section_name(line):
    # Because some miscellaneous info are also tagged as regular paragraphs, need a wordcount so that they don't
    # get added as a section name or appended to an existing one
    # Ex. HRS 84 number 43 and the tags the PREAMBLE is in
    # http://www.capitol.hawaii.gov/hrscurrent/Vol02_Ch0046-0115/HRS0084/HRS_0084-.htm
    words = line.split()
    count = 0
    for word in words:
        count += 1
    return count


def scrape_toc():
    base_url = 'http://www.capitol.hawaii.gov/docs/HRS.htm'
    html_to_parse = requests.get(base_url)
    soup = BeauSoup(html_to_parse.text, 'lxml')

    divisions = []
    titles = []
    chapters = []

    current_division = {}
    current_title = {}
    current_chapter = {}
    chapter_trigger = 0

    division_number = 1
    title_number = 1

    contents = soup.find_all('p', {'class': 'MsoNormal'})

    for content in contents:
        current_line = content.get_text().replace('\r\n ', "")
        if check_line(current_line):
            if "DIVISION" in current_line:
                if len(titles) > 0:
                    current_title["chapters"] = chapters
                    titles.append(current_title)

                    current_division["titles"] = titles
                    current_division["number"] = division_number
                    division_number = division_number + 1
                    divisions.append(current_division)

                    current_division = {}
                    current_title = {}
                    current_chapter = {}
                    titles = []
                    chapters = []

                    current_division["name"] = current_line
                else:
                    current_division["name"] = current_line

            elif "TITLE" in current_line:
                if len(chapters) > 0:
                    current_title["chapters"] = chapters
                    titles.append(current_title)

                    current_title = {}
                    current_chapter = {}
                    chapters = []

                    current_title["name"] = current_line
                    title_number = re.search(
                        '(([0-9]+)([A-Z])?)', current_line).group(0)
                    current_title["number"] = title_number
                else:
                    current_title["name"] = current_line
                    title_number = re.search(
                        '(([0-9]+)([A-Z])?)', current_line).group(0)
                    current_title["number"] = title_number
            else:
                if chapter_trigger == 0:
                    current_chapter["number"] = current_line
                    current_chapter["name"] = ""
                    chapter_trigger = 1

                elif chapter_trigger == 1:
                    current_chapter["name"] = current_line
                    chapter_url = content.a['href']
                    sections = scrape_section_names(chapter_url)
                    if sections is not None:
                        current_chapter['repealed'] = False
                        current_chapter['sections'] = sections
                    else:
                        current_chapter['repealed'] = True

                    chapters.append(current_chapter)
                    current_chapter = {}
                    chapter_trigger = 0

    current_title["chapters"] = chapters
    titles.append(current_title)

    current_division["titles"] = titles
    current_division["number"] = division_number
    division_number = division_number + 1
    divisions.append(current_division)

    return divisions


def main():
    divisions = scrape_toc()

    file_name = 'output/' + version + '.json'
    if no_text:
        file_name = 'output/' + version + '_notext.json'

    outfile = open(file_name, 'w')
    json.dump(divisions, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into " + file_name)


if __name__ == '__main__':
    main()
