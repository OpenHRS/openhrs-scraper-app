# OpenHRS Scraper App

## Installation and Running it

It would be recommended to create a virtual environment to hold all the dependencies.

1. To create your virtual environment through pip:

Make sure you have Python 3.6+ installed on your computer

```
pip install virtualenv
virtualenv env
source env/bin/activate
```

2. To install the dependencies:
```
python pip install -r requirements.txt
```

3. To run it:
```
python create_hrs_tree.py
```
It will output an hrsTree.json file with all the Divisions, Titles, Chapters, and Section names + numbers in a tree format.


## Plans
1. Add support for:

* Subtitles
* Articles
* Parts

Very few statutes are classified under these and it does not affect the overall statute data scraped.

2. Scrape individual statutes and along with hrsTree, transform it into a file structure shown by example in the corresponding folder.
