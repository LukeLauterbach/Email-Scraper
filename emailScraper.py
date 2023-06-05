import csv
import os
import urllib.request
from urllib.error import HTTPError
import re
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import InvalidArgumentException, WebDriverException
import html


# ---------------#
# VARIABLES      #
# ---------------#


# Define colors used for console output
class bColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Variables
debug_mode = False
delay_mode = False
delay = 0
domain = ''
email_database = []
email_database_file = ''
line_count = 0
num_pages_to_spider = 1000000000
parameter_mode = False
url_database_file = ''

chrome_options = Options()
#chrome_options.add_argument("--headless=new")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
browser = webdriver.Chrome(options=chrome_options)


# ---------------#
# FUNCTIONS      #
# ---------------#


def check_for_http(l_url):
    if not l_url.startswith("http"):
        l_url = f"https://{l_url}"  # TODO: Fix this to allow non-https
    return l_url


def check_if_files_exist(l_email_database_file, l_url_database_file, l_base_url):
    try:
        open(url_database_file)
    except FileNotFoundError:
        with open(url_database_file, 'w') as temp:
            temp.write(f"{l_base_url},false")
    try:
        open(l_email_database_file)
    except FileNotFoundError:
        with open(l_email_database_file, 'w') as temp:
            pass


def get_next_url():
    global line_count
    line_count = 0
    if os.path.exists(url_database_file):
        with open(url_database_file, encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')

            for csv_row in csv_reader:
                if csv_row[1] == 'false':
                    return csv_row[0]
                line_count += 1
    else:
        with open(url_database_file, 'w') as document:
            pass
        return base_url


def mark_url_parsed(l_url):
    temp_url_database_file = f'temp-{url_database_file}'
    try:
        os.remove(temp_url_database_file)
    except OSError:
        pass
    os.rename(url_database_file, temp_url_database_file)
    with open(temp_url_database_file, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if row[0] == l_url:
                with open(url_database_file, 'a', encoding="utf-8") as fd:
                    fd.write(f'{row[0]},true\n')
            else:
                with open(url_database_file, 'a', encoding="utf-8") as fd:
                    fd.write(f'{row[0]},{row[1]}\n')
    os.remove(temp_url_database_file)


def page_parse(page_url):
    try:
        browser.get(page_url)
        if delay_mode:
            time.sleep(delay)
        page_html = browser.page_source
    except HTTPError as err:
        if err.code == 403:
            print(f"{bColors.FAIL}{err.code} Error. This likely means a WAF is preventing the script's traffic. "
                  f"{bColors.ENDC} {page_url}")
        elif debug_mode is True:
            print(f"{bColors.FAIL}{err.code} Error:{bColors.ENDC} {page_url}")
    except urllib.error.URLError:
        if debug_mode is True:
            print(f"{bColors.FAIL}DNS Lookup Failed:{bColors.ENDC} {page_url}")
    except WebDriverException:
        if debug_mode is True:
            print(f"{bColors.FAIL}Connection Timed Out:{bColors.ENDC} {page_url}")
    else:
        # Spider for Additional URLs
        urls = re.findall(r"href=\"(.+?)[\"\'\s]", page_html)
        for new_unchecked_url in urls:
            new_unchecked_url = html.unescape(new_unchecked_url)  # Convert HTML URL to URL
            # We don't want to infinitely spider the internet. This will check to make sure the URL is contained
            #   within the domain.
            url_should_be_parsed, new_unchecked_url = check_url(new_unchecked_url, domain, page_url)

            if url_should_be_parsed is True:
                url_match = False
                # Not treating parameters as individual pages reduces the number of web requests and eliminates
                #   a number of potential error scenarios. But the option is there for people who need it for a
                #   specific site where it might be necessary.
                if parameter_mode is False:
                    new_unchecked_url = new_unchecked_url.split('?')[0]
                new_unchecked_url = new_unchecked_url.removesuffix('/')

                with open(url_database_file, encoding="utf-8") as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    for csv_row in csv_reader:
                        if csv_row[0] == new_unchecked_url and url_match is False:
                            url_match = True
                if url_match is False:
                    with open(url_database_file, 'a', encoding="utf-8") as fd:
                        fd.write(f'{new_unchecked_url},false\n')

        # Hunt for Emails
        regex_string = "[A-zÀ-ÿ0-9._%+-]+\@" + domain
        emails = re.findall(regex_string, page_html)

        for new_unchecked_email in emails:
            email_match = False
            for existing_email in email_database:
                if new_unchecked_email.lower() == existing_email.lower() and email_match is False:
                    email_match = True
            if email_match is False:
                email_database.append(new_unchecked_email)
                with open(email_database_file, 'a') as fd:
                    fd.write(f'{new_unchecked_email}\n')

    mark_url_parsed(page_url)


def check_url(l_url, l_domain, l_old_url):
    url_should_be_parsed = False
    if l_url.startswith("/"):
        url_should_be_parsed = True

        l_base_domain = re.findall(r"(.+?\/\/[^\/]+)", l_old_url)

        l_new_unchecked_url = base_url + l_url
    elif l_domain in l_url and "mailto:" not in l_url and "@" not in l_url:
        url_should_be_parsed = True
        l_new_unchecked_url = l_url
    else:
        url_should_be_parsed = False
        l_new_unchecked_url = l_url

    l_new_unchecked_url = check_for_http(l_new_unchecked_url)

    return url_should_be_parsed, l_new_unchecked_url


def help_menu():
    print("Title: Email Scraper")
    print("Author: Luke Lauterbach - Sentinel Technologies")
    print("")
    print("Usage: python3 [script] [Domain to Search]")
    print("")
    print("Optional Options:")
    print("    -e:  Specify an email domain that is different than the root webpage being spidered.")
    print("    -r:  Root page to spider.")
    print("    -p:  Parameter Mode - By default, the script will ignore parameters in links."
          "With -p, parameters will be treated as individual links")
    print("    -n:  Number of pages to spider")
    print("    -o:  Output filename")
    print("    -d:  Add a delay between web requests (in seconds)")
    print("    -db:  Debug Output")
    quit()


def status_update(l_url_database, l_email_database):
    l_count_parsed = 0
    l_count_total = 0
    l_count_email = 0

    with open(l_url_database, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for csv_row in csv_reader:
            l_count_total += 1
    l_count_email = sum(1 for l_line in open(l_email_database))

    print(f"{line_count}/{l_count_total} URLs - {l_count_email} Emails")


def print_initial_output(l_url, l_domain, l_max):
    if l_max == 1000000000:
        l_max = "Unlimited"
    print("")
    print(f"{bColors.HEADER}{bColors.BOLD}Email Scraper{bColors.ENDC}")
    print("")
    print(f"Searching {l_url} for {l_domain} email addresses.")
    print(f"Maximum Number of Pages to Search: {l_max}\n")


def print_ending(l_email_database_file, l_url_database_file):
    count_email_final = sum(1 for l_line in open(l_email_database_file, encoding="utf-8"))
    count_url_final = sum(1 for l_line in open(l_url_database_file, encoding="utf-8"))
    if count_url_final > num_pages_to_spider:
        count_url_final = num_pages_to_spider
    print(f"\nSpidering Complete. {count_url_final} pages parsed, {count_email_final} emails found.")
    exit()


# ---------------#
# EXECUTION      #
# ---------------#

# Parse Arguments
for index, argument in enumerate(sys.argv[1:]):
    if argument == "--help" or argument == "-h":
        help_menu()
    elif argument == "-d" or argument == "--delay":
        delay_mode = True
        delay = float(sys.argv[index + 2])
    elif argument == "-db" or argument == "--debug":
        debug_mode = True
    elif argument == "-e" or argument == "--email":
        domain = sys.argv[index + 2]
        url_database_file = f"{domain}-url_database.csv"
        email_database_file = f"{domain}-email_database.csv"
    elif argument == "-n" or argument == "--number-pages":
        num_pages_to_spider = int(sys.argv[index + 2])
    elif argument == "-o" or argument == "--out-filename":
        url_database_file = f"{sys.argv[index + 2]}-url_database.csv"
        email_database_file = f"{sys.argv[index + 2]}-email_database.csv"
    elif argument == "-p" or argument == "--parameter-mode":
        parameter_mode = True
    elif argument == "-r" or argument == "--root-page":
        base_url = check_for_http(sys.argv[index + 2])
    elif sys.argv[index] in {'-d', '-r', '-n', '-o'}:
        pass
    else:
        if not domain:
            domain = argument
            base_url = check_for_http(argument)

print_initial_output(base_url, domain, num_pages_to_spider)

if not url_database_file:
    url_database_file = f"{domain}-url_database.csv"
if not email_database_file:
    email_database_file = f"{domain}-email_database.csv"
check_if_files_exist(email_database_file, url_database_file, base_url)

with open(email_database_file) as file:
    while line := file.readline().rstrip():
        email_database.append(line)

i = 0
while i < num_pages_to_spider:
    try:
        url = get_next_url()
        if url:
            page_parse(url)
        else:
            print_ending(email_database_file, url_database_file)
    except AttributeError:
        print_ending(email_database_file, url_database_file)
    except InvalidArgumentException:
        print_ending(email_database_file, url_database_file)
    if i % 100 == 0:
        status_update(url_database_file, email_database_file)
    i += 1

print_ending(email_database_file, url_database_file)

browser.quit()
