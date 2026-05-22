import subprocess
from sys import executable

def main(playwright, headless=False):
    # Only needed for the first time run, but won't error on later runs
    install = subprocess.run(
        [executable, "-m", "patchright", "install", "chromium"],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        details = (install.stderr or install.stdout).strip()
        raise RuntimeError(f"Patchright browser install failed: {details}")

    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    page.route("**/*.{png,jpg,jpeg,svg,gif}", lambda route: route.abort())

    return browser, context, page
