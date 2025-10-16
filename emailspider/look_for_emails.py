import re
from html import unescape

def main(page_html = "", domains=None):
    if not domains:
        return []

    # Normalize page text
    page_html = unescape(page_html or "")
    page_html = page_html.replace("</span>", "")  # quick cleanup of broken tags

    # Build a domain regex (exact matches only, no subdomains)
    domain_pattern = "|".join(re.escape(d.strip().lower().lstrip("@")) for d in domains if d)
    regex = re.compile(rf"[A-Za-zÀ-ÿ0-9._%+-]+@(?:{domain_pattern})(?=[^A-Za-z0-9-]|$)", re.IGNORECASE)

    # Find all matching addresses
    emails = regex.findall(page_html)

    # Deduplicate (set is fine since order doesn't matter)
    return list(set(e.strip().lower() for e in emails))