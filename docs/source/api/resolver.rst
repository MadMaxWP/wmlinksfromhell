Resolver
========

.. currentmodule:: wmlinksfromhell.resolver

.. autoclass:: Resolver
   :members:
   :special-members: __init__

Resolution result
-----------------

.. autoclass:: ResolutionResult
   :members:
   :special-members: __init__

Batch resolution
----------------

``Resolver.resolve_many()`` resolves a sequence of values using the existing
``resolve()`` behavior and optional source context.

Resolution result serialization
--------------------------------

``ResolutionResult.as_json()`` serializes the same payload returned by
``as_dict()`` using the package's standard JSON settings.

Long project prefixes
----------------------

``long_project_prefix=True`` makes project/language interwiki output use the
full project name, for example ``wikipedia:hi:Apple`` instead of
``w:hi:Apple``. The option is available on ``resolve()``, ``resolve_url()``,
``resolve_interwiki()``, and ``to_interwiki()``. Long project/language input
is accepted and resolves to the same destination as the short form.
