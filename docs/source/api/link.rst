Link
====

.. currentmodule:: wmlinksfromhell.nodes

.. autoclass:: WMLink
   :members:
   :special-members: __init__
   :exclude-members: leading_colon,is_wikilink,is_external_link,is_category_link,is_file_link,is_self_link,is_wikimedia,is_wiki,is_external,is_url,is_bare_url,is_wiki_url,is_external_url,is_interwiki,is_local,is_revision,is_diff,is_action,is_service,is_tool,is_comment,has_title,has_revision,has_diff,has_action,is_project_prefix,is_language_prefix,is_language_project

Boolean checks
--------------

These properties provide quick checks for the syntax, destination, and other
characteristics of a link.

Syntax
------

.. autoattribute:: WMLink.is_wikilink

True when the parsed node is a wikilink.

.. autoattribute:: WMLink.is_external_link

True when the parsed node is an external-link node.

.. autoattribute:: WMLink.leading_colon

True when the wikilink has a leading colon.

Destination checks
-----------

.. autoattribute:: WMLink.is_wikimedia

True when the destination is a Wikimedia project.

.. autoattribute:: WMLink.is_wiki

True when the destination type is a wiki.

.. autoattribute:: WMLink.is_interwiki

True when the link resolves as an interwiki wikilink.

.. autoattribute:: WMLink.is_local

True when the link resolves as a local wikilink.

.. autoattribute:: WMLink.is_service

True when the destination is a Wikimedia service.

.. autoattribute:: WMLink.is_tool

True when the destination is a Wikimedia tool.

.. autoattribute:: WMLink.is_self_link

True when the destination is on the source wiki.

URL checks
----------

These properties distinguish URL syntax from the kind of destination the URL
resolves to.

.. autoattribute:: WMLink.is_url

True when the link uses URL syntax, including bare and bracketed URLs.

.. autoattribute:: WMLink.is_bare_url

True when the link is a bare, unbracketed URL.

.. autoattribute:: WMLink.is_wiki_url

True when the link uses URL syntax and resolves to a wiki.

.. autoattribute:: WMLink.is_external_url

True when the link uses URL syntax and resolves to an external destination.

.. autoattribute:: WMLink.is_external

Compatibility alias for ``is_url``. It does not mean that the destination is
an external site.

Special cases
-------------

.. autoattribute:: WMLink.is_revision

True when the link has revision information.

.. autoattribute:: WMLink.is_diff

True when the link has diff information.

.. autoattribute:: WMLink.is_action

True when the link has action information.

.. autoattribute:: WMLink.is_comment

True when the link is inside an HTML comment.

Links inside HTML comments are excluded from ``filter_links()`` by default.
Pass ``comment_links=True`` to include them. ``in_comment=True`` can then be
used to select links that are inside comments.

.. autoattribute:: WMLink.is_category_link

True when the link is a category link.

.. autoattribute:: WMLink.is_file_link

True when the link is a file link.

Other checks
------------

.. autoattribute:: WMLink.has_title

True when the link has a page title.

.. autoattribute:: WMLink.is_project_prefix

True when the resolved prefix is a project prefix.

.. autoattribute:: WMLink.is_language_prefix

True when the resolved prefix is a language prefix.

.. autoattribute:: WMLink.is_language_project

True when the resolved prefix identifies a language/project combination.

Compatibility aliases
----------------------

``has_revision`` is an alias for ``is_revision``.

``has_diff`` is an alias for ``is_diff``.

``has_action`` is an alias for ``is_action``.
