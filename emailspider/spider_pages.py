import os
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from patchright.sync_api import sync_playwright, TimeoutError
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from emailspider import dedupe_url_database, initialize_playwright, look_for_emails, check_urls


def main(email_db_file, url_db_file, url_database=None, email_database=None, root_page=None, domain=None,
         verbose=True, max_pages=0, debug_mode=False):
    total_pages_processed = sum(item["PARSED"] for item in url_database)
    pages_processed = 0
    url_database = assemble_url_database(url_database, root_page)
    dedupe_url_database.main(url_database)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn("Emails: {task.fields[emails]}"),
    )

    with progress:
        task_id = progress.add_task(
            "Spidering Pages",
            total=len(url_database),
            completed=total_pages_processed,
            emails=len(email_database),
        )

        with sync_playwright() as playwright:
            browser, context, page = initialize_playwright.main(playwright, headless=debug_mode)
            i = 0
            while i < len(url_database):
                entry = url_database[i]
                if entry["PARSED"]:
                    i += 1
                    continue

                observed_urls, observed_emails = page_parse(
                    url=entry["URL"],
                    browser=page,
                    verbose=verbose,
                    domain=domain,
                )
                observed_urls = check_urls.main(observed_urls, root_pages=root_page, source_url=entry["URL"])

                # Avoid appending duplicate URLs discovered from the same crawl pass.
                seen = {existing["URL"] for existing in url_database}
                for url in observed_urls:
                    if url not in seen:
                        url_database.append({"URL": url, "PARSED": False})
                        seen.add(url)

                email_database.extend(observed_emails)
                email_database = list(set(email_database))

                entry["PARSED"] = True
                pages_processed += 1
                total_pages_processed += 1

                if total_pages_processed % 25 == 0:
                    write_databases_to_file(email_db_file, email_database, url_db_file, url_database)

                progress.update(
                    task_id,
                    completed=total_pages_processed,
                    total=len(url_database),
                    emails=len(email_database),
                )

                if max_pages > 0 and pages_processed >= max_pages:
                    print(f"Hit page limit of {max_pages}.")
                    break

                i += 1

    write_databases_to_file(email_db_file, email_database, url_db_file, url_database)

    return url_database, email_database


def page_parse(url="", browser=None, verbose=False, domain=""):
    valid_urls = []

    url = ensure_scheme(url)

    page_html = ""

    try:
        browser.goto(url, timeout=7000)
        page_html = browser.content()
    except Exception:
        return [], []

    if not page_html:
        return [], []

    soup = BeautifulSoup(page_html, 'html.parser')
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        if href.startswith("mailto") or href.startswith("tel:") or not href:
            continue
        if href.startswith('/'):
            href = urljoin(url, href)
        valid_urls.append(href)

    emails_found = look_for_emails.main(page_html=page_html, domains=domain)
    return valid_urls, emails_found


def write_databases_to_file(email_db_file, email_database, url_db_file, url_database):
    if email_database:
        with open(email_db_file, "w", encoding="utf-8") as file:
            for email in email_database:
                file.write(f"{email}\n")
    elif os.path.exists(email_db_file) and os.path.getsize(email_db_file) == 0:
        os.remove(email_db_file)

    with open(url_db_file, "w", encoding="utf-8") as file:
        for url in url_database:
            file.write(f"{url['URL']},{url['PARSED']}\n")


def assemble_url_database(url_database, root_page):
    if url_database:
        return url_database

    for page in root_page:
        url_database.append({'URL': ensure_scheme(page), 'PARSED': False})

    return url_database


def ensure_scheme(url: str, default_scheme: str = "https") -> str:
    """Return a URL with a scheme, adding one if missing."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"{default_scheme}://{url}"
    return url
