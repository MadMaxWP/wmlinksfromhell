"""read normal links or links that live inside html comments."""

import wmlinksfromhell


text = """
<!-- [[w:en:Hidden]] -->
[[w:en:Visible]]
"""

code = wmlinksfromhell.parse(text, source="metawiki")

print("normal links:")
for link in code.filter_links():
    print(link.original)

print()
print("comment links:")
for link in code.filter_links(comment_links=True, in_comment=True):
    print(link.original)
