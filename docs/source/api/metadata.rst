Metadata
========

The metadata store provides wiki, namespace, language, and interwiki
lookups and manages cached Wikimedia metadata.

.. currentmodule:: wmlinksfromhell.metadata

.. autoclass:: MetadataStore
   :members:
   :special-members: __init__

Enumeration helpers
-------------------

``wikis_for_family()`` returns all known wikis in a family. ``languages()``
returns a copy of the known language mapping. ``canonical_namespaces()``
returns display-cased namespace names without changing the existing
casefolded namespace lookup APIs.

Knowledge and cache checks
--------------------------

The store supports membership checks with ``dbname in metadata`` and exposes
``is_stale()`` as a convenience wrapper around the metadata cache freshness
check.
