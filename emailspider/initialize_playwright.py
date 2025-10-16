import subprocess
from pathlib import Path
from sys import executable

def main(playwright, headless=False):
    patchright_cmd = Path(executable).parent / "patchright"

    # Only needed for the first time run, but won't error on later runs
    subprocess.run([patchright_cmd, "install"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.route("**/*.{png,jpg,jpeg,svg,gif}", lambda route: route.abort())

    return browser, context, page