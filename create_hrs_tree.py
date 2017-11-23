import json
import requests
import re
import sys
import math
from bs4 import BeautifulSoup as BeauSoup

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

####################################
#
# Multiple Line checking (to and ',')
#
####################################


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
        repealed_in_check_multiples(sections, chapter, multiples);
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
                        if re.search('\.[1-9]{2,}$', str(curr_section)) is not None:
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

####################################
#
# Section Scraping
#
####################################


def prep_section_name_data(url):
    """ Preps the data by getting rid of bolded text """
    base_url = url
    try:
        html_to_parse = requests.get(base_url)
        soup = BeauSoup(html_to_parse.text, 'lxml')
    except:
        html_to_parse = requests.get(base_url)
        soup = BeauSoup(html_to_parse.text, 'lxml')

    # Prep the data by taking out the chapter title in bold
    bold_titles = soup.find_all('b')
    leftover_text = ""
    get_stuff = False
    for bold_title in bold_titles:
        if bold_title.get_text():
            if get_stuff is False:
                leftover_text = ""

            rgx_code = re.search(
                '([\d\w]+)-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w)|(\d+))|(\d+:\d+\w?-\d+\w?)',
                bold_title.get_text())

            if "REPEALED" in bold_title.get_text() or rgx_code is not None:
                continue

            bold_title.decompose()

    if version in VERSIONS[-4:]:
        return soup.find_all('p')
    else:
        return soup.find_all('p', {'class': 'RegularParagraphs'})


def scrape_section_names(url):
    sections = []
    url = url.replace('hrscurrent', version)

    # Validate URL. If 404, get similar URL.
    if requests.get(re.search('.*Ch\d{4}\w?-\d{4}\w?/', url).group(0)).status_code == 404:
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

    line_data = prep_section_name_data(url)

    curr_section_name = ""
    curr_chapter_section = ""

    # Go through each line (<p> tags) and associate the data
    for line in line_data:
        clean_line = cleanup_text(line).strip()

        # Looks for statute code in Regex ex. 123-45.5
        rgx_code = re.search(
            '([\d\w]+)-((\d+\.\d+\w+)|(\d+\.\d+)|(\d+\w)|(\d+))|(\d+:\d+\w?-\d+\w?)',
            clean_line)

        if rgx_code is not None:
            # If something is being tracked already, append it
            if curr_section_name != "" and curr_chapter_section != "":
                append_section(sections, curr_chapter_section, curr_section_name, url)

            # If space does not separate chapter-section and section name
            # do something about it
            extra_text = re.search(
                '(\d+[A-Z]?-\d+(\.\d)?[A-Z]?)([A-Z][a-z]+$)',
                clean_line)
            if extra_text is not None:
                clean_line = clean_line.replace(
                    extra_text.group(1), extra_text.group(1) + ' ')

            # The section name is the current line - the statute code
            curr_section_name = clean_line.replace(
                rgx_code.group(0), '').strip()
            curr_chapter_section = rgx_code.group(0).split('-')

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
                curr_chapter_section[1] = frags[1] + '-' + curr_chapter_section[1]

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
                    curr_chapter_section[1] = curr_chapter_section[1].replace(end_punc.group(0), "")
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


def get_section_text_data(url, section):
    """ Prepares the data by getting rid of bold text """
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

    base_url = url.replace('.htm', section_url)

    good = True

    while text_data is None:
        try:
            html_to_parse = requests.get(base_url)
            soup = BeauSoup(html_to_parse.text, 'lxml')

            if good is False:
                print("Reconnection to " + base_url + " SUCCESSFUL...")
                good = True
            text_data = soup.find('body')
        except:
            # Reconnect on connection timeout
            print("Connection timeout on: " + base_url + " RECONNECTING...")
            good = False
            text_data = None

    if text_data is not None:
        text_data = text_data.get_text().replace('\r\n', ' ').strip()

    return text_data


def append_section(sections, chapter_section, section_name, url):
    """ Appends a section to a parent Section list """
    if url is not None and not no_text:

        # Check for excess text in section number string...
        excess_text = re.search(
            "(\d+(\.\d)?[A-Z]?)([A-Z][a-z]+$)", chapter_section[1])

        # ... and delete excess text if it exists
        if excess_text is not None:
            chapter_section[1] = chapter_section[1].replace(excess_text.group(3), '')

        text = get_section_text_data(url, chapter_section[1])
        section = {"number": chapter_section[1],
                   "name": section_name}
        if text is not None:
            if "Page Not Found" in text:
                print("Error 404 for: " +
                      (chapter_section[0]) + '-' + chapter_section[1])
            else:
                # The code explains everything.
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

                # Check for brackets
                brackets = re.search('^\[\]', text)
                if brackets is not None:
                    text = text.replace(brackets.group(0), '')
                elif '[' in text and text.find('[') == 0 and ']' in text:
                    text = text[(text.find(']') + 1):]
                elif '[' in text and text.find('[') == 0 and u'\u00a0' in text:
                    text = text[(text.find(u'\u00a0') + 1):]

                text = text.strip()

                # Check for brackets again
                brackets = re.search('^\[\]', text)
                if brackets is not None:
                    text = text.replace(brackets.group(0), '')
                elif '[' in text and text.find('[') == 0 and ']' in text:
                    text = text[(text.find(']') + 1):]
                elif '[' in text and text.find('[') == 0 and u'\u00a0' in text:
                    text = text[(text.find(u'\u00a0') + 1):]

                section['text'] = text
                sections.append(section)

        else:
            print("Error parsing text for: " +
                  (chapter_section[0]) + '-' + chapter_section[1])

    else:
        section = {"number": chapter_section[1],
                   "name": section_name}

        if not no_text:
            section['text'] = None
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
                        '(([0-9]+)([A-Z]))|([0-9]+)', current_line).group(0)
                    current_title["number"] = title_number
                else:
                    current_title["name"] = current_line
                    title_number = re.search(
                        '(([0-9]+)([A-Z]))|([0-9]+)', current_line).group(0)
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
