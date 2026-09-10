"""small examples of the simple public api."""

import wmlinksfromhell


wiki = wmlinksfromhell.wiki("enwiki")
print(wiki.language)
print(wiki.project)
print(wiki.interwiki("Apple"))
print(wiki.page_url("Apple"))
print(wiki.link("Apple", "the fruit"))

info = wmlinksfromhell.interwiki("enwiki")
print(info.prefix)
print(info.project)
print(info.language)

print(wmlinksfromhell.url("dewiki", "Apfel"))
print(wmlinksfromhell.link("dewiki", "Apfel", "Apfel"))
