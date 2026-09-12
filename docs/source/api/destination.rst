Destination
===========

.. currentmodule:: wmlinksfromhell.destination

.. autoclass:: Destination
   :members:
   :special-members: __init__

Destination type
----------------

``destination_type`` identifies what the destination represents, such as a
wiki, service, tool, or external destination.

Wiki information
----------------

These fields describe the Wikimedia or MediaWiki wiki when that information
is available:

* ``family``
* ``project``
* ``language``
* ``dbname``
* ``wikiid``
* ``hostname``

Page information
----------------

These fields describe the target page and page-related operations:

* ``title``
* ``namespace``
* ``fragment``
* ``page_id``
* ``revision``
* ``diff``
* ``action``
* ``special_page``

Service information
-------------------

These fields are used for non-wiki destinations such as Wikimedia services
and tools:

* ``organization_name``
* ``service_name``

Other information
------------------

* ``query_parameters``
* ``canonical_url``
* ``metadata_source``

Project flags
-------------

These flags describe properties of the destination's wiki/project:

* ``is_multilingual``
* ``is_standard_project``
* ``is_wikimedia_project``

Identity and operation helpers
------------------------------

* ``full_title``
* ``is_revision``
* ``is_diff``
* ``is_action``
* ``page_identity_key()``
* ``identity_key()``
* ``same_page_as()``
* ``as_dict()``
* ``as_json()``

Serialization
-------------

``from_dict()`` reconstructs a destination from the mapping returned by
``as_dict()``, including conversion of the destination type and query
parameters back to their native types. ``as_dict()`` and ``as_json()`` remain
available for serialization.

Destination type checks
-----------------------

``is_wiki``, ``is_external``, and ``is_unknown`` provide direct boolean checks
for the corresponding destination types.
