"""print the canonical interwiki target and url for every SiteMatrix wiki."""

import wmlinksfromhell as wm


TITLE = "MediaWiki:Gadget:Xtools.js"

metadata = wm.Metadata()
metadata.update_sitematrix()

for wiki in sorted(metadata.all_wikis(), key=lambda item: item.dbname):
    info = metadata.interwiki(wiki.dbname)

    if info is None:
        print(f"{wiki.dbname} → [NO PREFIX]")
        continue

    try:
        target = info.target(TITLE)
        url = wiki.page_url(TITLE, metadata=metadata)
    except Exception as error:
        print(f"{wiki.dbname} → {info.prefix}: ERROR {error}")
        continue

    print(f"{wiki.dbname} → {target} - {url}")
