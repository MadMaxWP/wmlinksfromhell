"""optional Pywikibot integration"""

import pywikibot

import wmlinksfromhell


site = pywikibot.Site("meta", "meta")
page = pywikibot.Page(site, "Steward requests/Miscellaneous")
code = wmlinksfromhell.parse(page.text, source=site)

for link in code.filter_links():
    print(link.raw, link.family, link.language, link.dbname, link.title)
