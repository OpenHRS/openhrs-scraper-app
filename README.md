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
python create_hrs_tree.py <notext> <hrs[current|year]>
```
Given a year, it will output a file named `hrs[current|year][_notext].json`. 
When passed the `notext` option, it will scrape names statute names only.

Examples:
```
python create_hrs_tree.py notext hrscurrent
```
It will output a file named `hrscurrent.json` with all the current Divisions, Titles, Chapters, and Section names + numbers in a tree format. Notice the `notext` arg will not output section text.

```
python create_hrs_tree.py hrs2016
```
Similarly, will ouput a file named `hrs2016.json` with the data as `notext` along with section text.

## Testing
For development purposes only, testing scripts have been created named `testing_xxxx.py` where xxxx is the data to be tested. These scripts will output a similar json file named `testing_xxxx.py` with the resulting data.

## Plans
1. Add support for:

* Subtitles
* Articles
* Parts

Very few statutes are classified under these and it does not affect the overall statute data scraped.
