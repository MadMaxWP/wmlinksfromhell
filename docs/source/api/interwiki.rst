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

.. autofunction:: render_local_target
