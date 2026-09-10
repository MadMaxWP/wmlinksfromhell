"""convert only the selected Wikimedia links in a text fragment"""

import wmlinksfromhell


text = "[[w:en:Apple|this article]] https://de.wikipedia.org/wiki/Berlin https://example.com/leave-me"
code = wmlinksfromhell.parse(text, source="enwiki")

for link in code.filter_links(family="wikipedia", language="en"):
    link.set_interwiki()

print(code)
