from urllib.parse import urlparse, urlunparse

def main(list_of_urls, root_pages=None, source_url=""):
    if root_pages is None:
        root_pages = []
    else:  # Get rid of the schemes
        root_pages = [urlparse(url).netloc for url in root_pages]

    invalid_prefixes = [
        "tel:", "http://webcal://", "https://webcal://", "mailto:", "#", "javascript",
        "javascript://", "webcal://", "zoom://"
    ]

    invalid_filetypes = [
        ".css", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".tif", ".tiff",
        ".webp", ".bmp", ".ico", ".apng", ".heif", ".heic"
    ]

    valid_urls = []

    for url in list_of_urls:
        # Skip any URLs that start with invalid prefixes
        if any(url.lower().startswith(prefix) for prefix in invalid_prefixes):
            continue

        # Skip any URLs that end with invalid prefixes
        parsed_url = urlparse(url)
        if any(parsed_url.path.lower().endswith(ext) for ext in invalid_filetypes):
            continue

        if isinstance(source_url, str):
            source_url = urlparse(source_url)

        scheme = parsed_url.scheme if parsed_url.scheme else source_url.scheme
        hostname = parsed_url.netloc.lower() if parsed_url.netloc else source_url.netloc.lower()

        # Handle relative URLs (no hostname)
        if not hostname:
            continue
        elif not any(allowed in hostname for allowed in root_pages):
            # URL's hostname doesn't match allowed root domains
            continue
        else:
            # Rebuild the URL without fragment
            url = urlunparse((scheme, hostname, parsed_url.path, parsed_url.params, parsed_url.query, ''))
            valid_urls.append(url)

    return valid_urls