Interwiki
=========

The interwiki classes describe available prefixes and individual interwiki
configuration entries.

.. currentmodule:: wmlinksfromhell.metadata

InterwikiMap
------------

.. autoclass:: InterwikiMap
   :members:
   :special-members: __init__

InterwikiEntry
--------------

.. autoclass:: InterwikiEntry
   :members:
   :special-members: __init__

Lower-level interwiki results and helpers
-----------------------------------------

.. currentmodule:: wmlinksfromhell.interwiki

.. autoclass:: ChainResult

.. autofunction:: resolve_chain

.. autofunction:: is_local_to

.. autofunction:: render_interwiki_target

``long_project_prefix=True`` renders a full project name such as
``wikipedia:hi:Apple`` instead of the default ``w:hi:Apple``.

.. autofunction:: render_local_target

Prefix enumeration
------------------

``InterwikiMap.prefixes()`` returns the known interwiki prefixes for the map as
a read-only set.
