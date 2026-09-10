"""exceptions used when a requested operation cannot be completed"""


class WMLinksFromHellError(Exception):
    """base exception for the package"""


class MetadataMissingError(WMLinksFromHellError):
    """required Wikimedia metadata is not available"""


class ConversionError(WMLinksFromHellError):
    """a destination cannot be safely rendered in the requested form"""


class CacheError(WMLinksFromHellError):
    """the metadata cache could not be written or managed"""


class SourceResolutionError(WMLinksFromHellError):
    """the supplied source wiki could not be identified"""


class ResolutionError(WMLinksFromHellError):
    """strict resolution was requested but the result was not resolvable"""


# deprecated spelling kept for compatibility; use WMLinksFromHellError
WMLinkFromHellError = WMLinksFromHellError
