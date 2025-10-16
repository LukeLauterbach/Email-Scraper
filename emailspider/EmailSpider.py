import argparse
import os
from urllib.parse import urlparse, urljoin
import re
import logging
from patchright.sync_api import Playwright, sync_playwright, expect, Error
from patchright._impl._errors import TimeoutError, TargetClosedError
from time import sleep
from emailspider import spider_pages


class Colors:  # Define colors used for console output
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_variables(domain="", root_page="", output_directory="", get_file_ext="", num_pages=0, verbose=False):
    if not root_page:
        root_page = domain
    if not num_pages:
        num_pages = 1000000000
    else:
        num_pages = int(num_pages)
    if not output_directory:
        output_directory = os.getcwd()
    if get_file_ext:
        get_file_ext = get_file_ext.lower()
        get_file_ext = get_file_ext.split(",")
    else:
        get_file_ext = ["pdf", "doc", "dot", "wbk", "docx", "docm", "dotx", "dotm", "docb", "xlt", "wlm", "xlsx",
                        "xlsm", "xltx", "xltm", "ppt", "pot", "pps", "pptx", "pptm", "potx", "potm", "one", "pub",
                        "xps"]

    if isinstance(root_page, str):
        root_page = root_page.split(",")
    if isinstance(domain, str):
        domain = domain.split(",")
    # Ensure each root page has a scheme for Selenium
    root_page = [spider_pages.ensure_scheme(p) for p in root_page]
    # Lowercase all of the domains
    root_page = [p.lower() for p in root_page]

    domain = [d.lower() for d in domain]

    email_db_file = os.path.join(output_directory, f"{domain[0]}-emails.csv")
    page_db_file = os.path.join(output_directory, f"{domain[0]}-urls.csv")

    return (root_page, num_pages, output_directory, get_file_ext, email_db_file, page_db_file)


def main(domain="",  # There has to be a better way to format this.
         root_page="",
         num_pages=1000000000,
         output_directory=None,
         verbose=False,
         get_file_mode=False,
         get_file_ext="",
         get_file_max=0,
         debug_mode=False):
    if not domain:
        (root_page, num_pages, output_directory, get_file_mode, get_file_ext, get_file_max,
         verbose_mode, domain, debug_mode) = parse_arguments()

    (root_page,
     num_pages,
     output_directory,
     get_file_ext,
     email_db_file,
     page_db_file) = process_variables(domain=domain,
                                       num_pages=num_pages,
                                       root_page=root_page,
                                       output_directory=output_directory,
                                       get_file_ext=get_file_ext,
                                       verbose=verbose)

    print_initial_output(num_pages=num_pages, root_page=root_page, domain=domain, verbose=verbose)

    email_database, url_database = read_databases(email_db_file=email_db_file, page_db_file=page_db_file,
                                                  verbose=verbose, root_page=root_page)
    try:
        url_database, email_database = spider_pages.main(email_db_file, page_db_file, url_database=url_database,
                                                    email_database=email_database, root_page=root_page, domain=domain,
                                                    verbose=verbose, max_pages=num_pages, debug_mode=debug_mode)
    except KeyboardInterrupt:
        pass

    if get_file_mode:
        get_files(get_file_ext, url_database, verbose, get_file_max)

    print_ending(url_database, email_database, email_db_file, page_db_file, get_file_mode)
    return email_database



def get_files(get_file_ext, url_database, verbose, get_file_max, get_file_dir="downloaded_files"):
    files_to_get     = get_file_urls(get_file_ext, url_database)
    num_files_to_get = min(len(files_to_get), get_file_max)

    print(f"\nPreparing to download {num_files_to_get} files to {get_file_dir!r}.")
    os.makedirs(get_file_dir, exist_ok=True)

    # pre‐populate the set of already downloaded filenames
    existing = set(os.listdir(get_file_dir))

    with sync_playwright() as pw:
        # launch a persistent context so downloads_path works
        context = pw.chromium.launch_persistent_context(
            user_data_dir="user_data",
            headless=True,
            accept_downloads=True,
            downloads_path=get_file_dir,
        )
        page = context.new_page()

        for url in files_to_get[:num_files_to_get]:
            # derive a fallback filename from the URL
            fname = os.path.basename(urlparse(url).path)
            if not fname:
                if verbose:
                    print(f"⚠ could not infer filename from {url!r}, skipping")
                continue

            if fname in existing:
                if verbose:
                    print(f"✔ already have {fname}, skipping")
                continue

            try:
                # wait up to 5 s for the browser to fire a download event
                with page.expect_download(timeout=5000) as dl_info:
                    try:
                        page.goto(url, timeout=7000)
                    except Error as nav_err:
                        # swallow the "navigation aborted" error for attachments
                        if "ERR_ABORTED" in str(nav_err):
                            if verbose:
                                print(f"⚠ navigation aborted for {url!r}, skipping")
                            # jump to next URL
                            continue
                        # other navigation errors should bubble
                        raise

                download = dl_info.value
                # use whatever the server suggests, or fallback to fname
                save_name = download.suggested_filename or fname
                dest = os.path.join(get_file_dir, save_name)
                download.save_as(dest)
                existing.add(save_name)
                print(f"✔ saved {save_name}")

            except TimeoutError:
                # no download event in 5 s
                if verbose:
                    print(f"⚠ no download event for {url!r}, skipping")
                continue
            except TargetClosedError:
                print(f"⚠ browser closed unexpectedly while handling {url!r}, skipping")

        # make sure we close the context before exiting sync_playwright
        sleep(1)
        context.close()

    print(f"{len(existing)} files now in {get_file_dir!r}.")


def get_file_urls(get_file_ext, url_database):
    get_file_ext = tuple(get_file_ext)
    files_to_get = []

    for entry in url_database:
        url = entry['URL']
        url = url.split("?")[0]
        if url.lower().endswith(get_file_ext):
            files_to_get.append(url)

    return files_to_get


def print_ending(url_database, email_database, email_db_file, page_db_file, get_file_mode):
    print(f"\nSpidering complete. {len(url_database)} URLs parsed, {len(email_database)} unique emails found.")
    print(f"URLs written to: {page_db_file}")
    print(f"Emails written to: {email_db_file}")
    if get_file_mode:
        print(f"Downloaded files written to: downloaded_files")


def read_databases(email_db_file="", page_db_file="", verbose=False, root_page=None):
    email_database, page_database = [], []
    try:
        with open(page_db_file, encoding="utf-8") as file:
            while line := file.readline():
                line = line.rstrip()
                line = line.split(",")
                parsed = line[1].lower() == 'true'
                page_database.append({"URL": line[0], "PARSED": parsed})
        if verbose:
            print("Existing URL Database Found.")
    except FileNotFoundError:
        for page in root_page:
            page_database.append({"URL": page, "PARSED": False})
    try:
        with open(email_db_file, encoding="utf-8") as file:
            while line := file.readline():
                line = line.rstrip()
                email_database.append(line)
        if verbose:
            print("Existing Email Database Found.")
    except FileNotFoundError:  # No need to do anything if the file doesn't exist
        pass

    return email_database, page_database


def print_initial_output(num_pages=0, root_page="", domain="", verbose=False):
    if num_pages == 1000000000:
        max_num_pages_display = "Unlimited"
    else:
        max_num_pages_display = num_pages
    print(f"\n{Colors.HEADER}{Colors.BOLD}Email Scraper{Colors.ENDC}\n")
    print(f"Searching {root_page} for {domain} email addresses.")
    if verbose:
        print(f"Verbose Mode: True")
    print(f"Maximum Number of Pages to Search: {max_num_pages_display}\n")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Spider pages and find email addresses in the pages')

    parser.add_argument('domain', nargs='?', help="Domain to Spider (e.g. example.com). If multiple domains, separate with commas. All domains will be parsed for email addresses using any of the specified domains.")
    parser.add_argument('-r', dest="root_page", help="Root Page (if different than domain).")
    parser.add_argument('-n', dest="num_pages", default=1000000000, help="Number of Pages to Spider")
    parser.add_argument('-od', dest="output_directory", help="Directory to Store Files")
    parser.add_argument('-gf', dest="get_file_mode", action="store_true",
                        help="Get files to be used with ExifTool")
    parser.add_argument('-gfe', dest="get_file_ext", help="Manually specify file extenions to get")
    parser.add_argument('-gfm', dest="get_file_max", default=100000,
                        help="Max Files to Get (Defaults to Unlimited)")
    parser.add_argument('-v', dest='verbose_mode', action="store_true", help="Verbose Mode")
    parser.add_argument('-db', dest='debug_mode', action="store_true", default=False, help="Turn on Debugging")

    args = parser.parse_args()

    args.num_pages = int(args.num_pages)
    args.get_file_max = int(args.get_file_max)

    domain = args.domain
    if not domain:
        domain = input("Please enter the domain: ").strip()

    return (args.root_page, args.num_pages, args.output_directory, args.get_file_mode, args.get_file_ext,
            args.get_file_max, args.verbose_mode, domain, args.debug_mode)


if __name__ == '__main__':
    main()
