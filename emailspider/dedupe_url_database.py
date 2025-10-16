from collections import OrderedDict

def main(url_database):
    """
    Remove duplicate URLs from url_database in place,
    preserving first-seen order.  If any duplicate
    had PARSED=True, the kept entry’s PARSED will be True.
    """
    deduped = OrderedDict()
    for entry in url_database:
        url    = entry['URL']
        parsed = entry.get('PARSED', False)
        if url in deduped:
            # once True, always True
            deduped[url] = deduped[url] or parsed
        else:
            deduped[url] = parsed

    # rebuild the list
    url_database[:] = [
        {'URL': url, 'PARSED': parsed}
        for url, parsed in deduped.items()
    ]