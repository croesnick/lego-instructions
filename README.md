# `lego-instructions`

Downloader script for LEGO instructions.
Fetches the instruction manuals by parsing the LEGO download page.
Use at your own risk. 😇

## Requirements

- Install the required packages: `pip install -r requirements.txt`
- Install playwright: `playwright install`

## Usage

Start the script with a comma-separated list of set numbers to fetch:

```shell
python download.py 71741,71795,71799
```

## Noteworthy

Has been hacked together quickly just to get the build instructions.

Moreover, the script expects the German page for scraping (it searches for the German term for "build instructions": "Bauanleitungen").
Adjust it to your needs. 😊
