API references
==============

The reference is generated from the package itself, so signatures, classes,
and their members stay tied to the actual API.

The main API areas are:

.. toctree::
   :maxdepth: 2

   api/package
   api/parser
   api/link
   api/resolver
   api/metadata
   api/cache
   api/models
   api/destination
   api/interwiki
   api/url
   api/pywikibot
   api/exceptions

Main public API
---------------

.. currentmodule:: wmlinksfromhell

.. autosummary::
   :nosignatures:

   parse
   parse_page
   resolve
   resolve_url
   resolve_interwiki
   to_url
   to_interwiki
   to_local
   wiki
   wikis
   interwiki
   url
   link

   Code
   Link
   Wiki
   WikiInfo
   WMCode
   WMLink

   Result
   ResolutionResult

   Metadata
   MetadataStore
   MetadataCache

   Resolver
   Destination

   InterwikiMap
   InterwikiEntry
   InterwikiInfo

   DestinationType
   ResolutionStatus
   SyntaxType

   WMLinksFromHellError
   WMLinkFromHellError
   Error

   ConversionError
   MetadataMissingError
   CacheError
   SourceResolutionError
   ResolutionError
