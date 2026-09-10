"""select links by structure, then inspect only those links."""

import wmlinksfromhell


text = """== Requests ==
* delete [[w:en:Apple]] because of the reason [[User:Example]]
* delete https://de.wikipedia.org/wiki/Berlin because of the reason [[User:Example]]
{{Request|target=[[w:fr:Paris]]}}
"""

code = wmlinksfromhell.parse(text, source="metawiki")

# the parser keeps its normal structure, so scope first
# and then decide which links are interesting.
section = next(section for section in code.get_sections() if section.wikicode.filter_headings())

for link in section.filter_links(predicate=lambda item: item.is_wikimedia):
    print(link.raw, link.family, link.language, link.dbname, link.title)
