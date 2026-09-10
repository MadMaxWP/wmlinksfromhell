Link
====

.. currentmodule:: wmlinksfromhell.nodes

.. autoclass:: WMLink
   :members:
   :special-members: __init__

Boolean checks
--------------

These properties are useful for checking the kind of link that was parsed
or the kind of destination it resolves to.

**Syntax**

* ``is_wikilink`` — the parsed node is a wikilink.
* ``is_external_link`` — the parsed node is an external-link node.

**Destination and URL**

* ``is_wikimedia`` — the destination is a Wikimedia project.
* ``is_wiki`` — the destination type is a wiki.
* ``is_external`` — the original syntax is a URL.
* ``is_url`` — the link uses URL syntax.
* ``is_bare_url`` — the link is a bare URL.
* ``is_wiki_url`` — the URL resolves to a wiki.
* ``is_external_url`` — the URL resolves to an external destination.
* ``is_interwiki`` — the link resolves as an interwiki wikilink.
* ``is_local`` — the link resolves as a local wikilink.

**Special cases**

* ``is_revision`` — the link has revision information.
* ``is_diff`` — the link has diff information.
* ``is_action`` — the link has action information.
* ``is_service`` — the destination is a Wikimedia service.
* ``is_tool`` — the destination is a Wikimedia tool.
* ``is_comment`` — the link is inside an HTML comment.
* ``is_category_link`` — the link is a category link.
* ``is_file_link`` — the link is a file link.
* ``is_self_link`` — the destination is on the source wiki.

**Other checks**

* ``has_title`` — the link has a page title.
* ``has_revision`` — the link has revision information.
* ``has_diff`` — the link has diff information.
* ``has_action`` — the link has action information.
* ``is_project_prefix`` — the resolved prefix is a project prefix.
* ``is_language_prefix`` — the resolved prefix is a language prefix.
* ``is_language_project`` — the resolved prefix identifies a language/project combination.
