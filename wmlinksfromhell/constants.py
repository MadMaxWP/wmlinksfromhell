"""bootstrap data; live Wikimedia metadata can extend/override this"""

from __future__ import annotations

from .models import WikiInfo

CACHE_SCHEMA_VERSION = 2

LANGUAGES: dict[str, str] = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "nl": "Dutch", "pl": "Polish", "ru": "Russian", "ja": "Japanese",
    "zh": "Chinese", "hi": "Hindi", "ar": "Arabic", "sv": "Swedish", "fi": "Finnish",
    "no": "Norwegian", "da": "Danish", "cs": "Czech", "uk": "Ukrainian", "he": "Hebrew",
    "ko": "Korean", "id": "Indonesian", "tr": "Turkish", "os": "Ossetian", "mul": "Multilingual",
    "az": "Azerbaijani", "ba": "Bashkir", "be": "Belarusian", "eo": "Esperanto", "hsb": "Upper Sorbian",
    "lez": "Lezghian", "tg": "Tajik", "udm": "Udmurt", "ms": "Malay", "tk": "Turkmen",
    "vls": "West Flemish", "dv": "Divehi", "ca": "Catalan", "fa": "Persian", "bn": "Bangla",
    "el": "Greek", "hu": "Hungarian", "ro": "Romanian", "sk": "Slovak", "sl": "Slovenian",
    "hr": "Croatian", "sr": "Serbian", "bg": "Bulgarian", "et": "Estonian", "lv": "Latvian",
    "lt": "Lithuanian", "is": "Icelandic", "ga": "Irish", "cy": "Welsh", "af": "Afrikaans", "simple": "Simple English",
}

MULTILINGUAL_FAMILIES: dict[str, dict[str, str]] = {
    "wikipedia": {"project": "wikipedia", "site_code": "wiki", "suffix": "wiki"},
    "wiktionary": {"project": "wiktionary", "site_code": "wiktionary", "suffix": "wiktionary"},
    "wikinews": {"project": "wikinews", "site_code": "wikinews", "suffix": "wikinews"},
    "wikibooks": {"project": "wikibooks", "site_code": "wikibooks", "suffix": "wikibooks"},
    "wikiquote": {"project": "wikiquote", "site_code": "wikiquote", "suffix": "wikiquote"},
    "wikisource": {"project": "wikisource", "site_code": "wikisource", "suffix": "wikisource"},
    "wikiversity": {"project": "wikiversity", "site_code": "wikiversity", "suffix": "wikiversity"},
    "wikivoyage": {"project": "wikivoyage", "site_code": "wikivoyage", "suffix": "wikivoyage"},
}

BOOTSTRAP_LANGS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "wikipedia": tuple(LANGUAGES) + ("simple",),
    "wiktionary": ("en", "de", "fr", "it", "fa", "simple"),
    "wikinews": ("en", "de"),
    "wikibooks": ("en", "de", "nl", "it", "simple"),
    "wikiquote": ("en", "de", "fr"),
    "wikisource": ("en", "de", "mul", "az"),
    "wikiversity": ("en", "de"),
    "wikivoyage": ("en", "de", "it"),
}

SINGLE_WIKIS: dict[str, dict] = {
    "commonswiki": dict(family="commons", project="commons", language="mul", hostname="commons.wikimedia.org", sitename="Wikimedia Commons"),
    "mulwikisource": dict(family="wikisource", project="wikisource", language="mul", hostname="wikisource.org", sitename="Wikisource multilingual"),
    "wikidatawiki": dict(family="wikidata", project="wikidata", language="mul", hostname="www.wikidata.org", sitename="Wikidata"),
    "metawiki": dict(family="meta", project="meta", language="en", hostname="meta.wikimedia.org", sitename="Meta-Wiki"),
    "mediawikiwiki": dict(family="mediawiki", project="mediawiki", language="en", hostname="www.mediawiki.org", sitename="MediaWiki.org"),
    "specieswiki": dict(family="wikispecies", project="wikispecies", language="mul", hostname="species.wikimedia.org", sitename="Wikispecies"),
    "incubatorwiki": dict(family="incubator", project="incubator", language="mul", hostname="incubator.wikimedia.org", sitename="Wikimedia Incubator"),
    "foundationwiki": dict(family="foundation", project="foundation", language="en", hostname="foundation.wikimedia.org", sitename="Wikimedia Foundation Governance Wiki"),
    "wikifunctionswiki": dict(family="wikifunctions", project="wikifunctions", language="mul", hostname="www.wikifunctions.org", sitename="Wikifunctions"),
    "wikitechwiki": dict(family="wikitech", project="wikitech", language="en", hostname="wikitech.wikimedia.org", sitename="Wikitech"),
    "strategywiki": dict(family="strategy", project="strategy", language="en", hostname="strategy.wikimedia.org", sitename="Wikimedia Strategic Planning"),
    "testwiki": dict(family="test", project="test", language="en", hostname="test.wikipedia.org", sitename="Test Wikipedia"),
    "betawikiversity": dict(family="wikiversity", project="wikiversity", language="en", hostname="beta.wikiversity.org", sitename="Beta Wikiversity"),
    "arbcom_cswiki": dict(family="special", project="arbcom_cswiki", language="cs", hostname="arbcom-cs.wikipedia.org", sitename="Czech Wikipedia Arbitration Committee wiki"),
    "arbcom_dewiki": dict(family="special", project="arbcom_dewiki", language="de", hostname="arbcom-de.wikipedia.org", sitename="German Wikipedia Arbitration Committee wiki"),
    "arbcom_enwiki": dict(family="special", project="arbcom_enwiki", language="en", hostname="arbcom-en.wikipedia.org", sitename="English Wikipedia Arbitration Committee wiki"),
    "arbcom_fiwiki": dict(family="special", project="arbcom_fiwiki", language="fi", hostname="arbcom-fi.wikipedia.org", sitename="Finnish Wikipedia Arbitration Committee wiki"),
    "arbcom_itwiki": dict(family="special", project="arbcom_itwiki", language="it", hostname="wikipedia-it-arbcom.wikimedia.org", sitename="Italian Wikipedia Arbitration Committee wiki"),
    "arbcom_nlwiki": dict(family="special", project="arbcom_nlwiki", language="nl", hostname="arbcom-nl.wikipedia.org", sitename="Dutch Wikipedia Arbitration Committee wiki"),
    "arbcom_plwiki": dict(family="special", project="arbcom_plwiki", language="pl", hostname="wikipedia-pl-arbcom.wikimedia.org", sitename="Polish Wikipedia Arbitration Committee wiki"),
    "arbcom_ruwiki": dict(family="special", project="arbcom_ruwiki", language="ru", hostname="arbcom-ru.wikipedia.org", sitename="Russian Wikipedia Arbitration Committee wiki"),
    "arbcom_zhwiki": dict(family="special", project="arbcom_zhwiki", language="zh", hostname="wikipedia-zh-arbcom.wikimedia.org", sitename="Chinese Wikipedia Arbitration Committee wiki"),
    "boardwiki": dict(family="special", project="boardwiki", language="en", hostname="board.wikimedia.org", sitename="Wikimedia Board wiki"),
    "checkuserwiki": dict(family="special", project="checkuserwiki", language="en", hostname="checkuser.wikimedia.org", sitename="CheckUser wiki"),
    "stewardwiki": dict(family="special", project="stewardwiki", language="en", hostname="steward.wikimedia.org", sitename="Steward wiki"),
    "wikimaniateamwiki": dict(family="special", project="wikimaniateamwiki", language="en", hostname="wikimaniateam.wikimedia.org", sitename="Wikimania Team wiki"),
    "arbcom_ukwiki": dict(family="special", project="arbcom_ukwiki", language="uk", hostname="wikipedia-uk-arbcom.wikimedia.org", sitename="Ukrainian Wikipedia Arbitration Committee wiki"),
}

COMMON_WIKIMEDIA_HOST_SUFFIXES = (
    ".wikipedia.org", ".wiktionary.org", ".wikinews.org", ".wikibooks.org", ".wikiquote.org",
    ".wikisource.org", ".wikiversity.org", ".wikivoyage.org", ".wikimedia.org", ".mediawiki.org",
    ".wikifunctions.org", ".wikitech.org", ".toolforge.org",
)

# Short family prefixes are context-sensitive: they can carry the source
# language when switching to another Wikimedia project family.
FAMILY_PREFIXES = {
    "w": "wikipedia",
    "wikt": "wiktionary",
    "n": "wikinews",
    "b": "wikibooks",
    "q": "wikiquote",
    "s": "wikisource",
    "v": "wikiversity",
    "voy": "wikivoyage",
}

# Long project names are actual interwiki entries and normally point at the
# English project. Keep them separate from context-sensitive short prefixes.
SINGLE_WIKI_PREFIXES = {
    "wikipedia": "enwiki",
    "wiktionary": "enwiktionary",
    "wikinews": "enwikinews",
    "wikibooks": "enwikibooks",
    "wikiquote": "enwikiquote",
    "wikisource": "enwikisource",
    "wikiversity": "enwikiversity",
    "wikivoyage": "enwikivoyage",
    "oldwikisource": "mulwikisource",
    "c": "commonswiki",
    "commons": "commonswiki",
    "d": "wikidatawiki",
    "wikidata": "wikidatawiki",
    "m": "metawiki",
    "meta": "metawiki",
    "metawiki": "metawiki",
    "metawikimedia": "metawiki",
    "metawikipedia": "metawiki",
    "mw": "mediawikiwiki",
    "mediawikiwiki": "mediawikiwiki",
    "species": "specieswiki",
    "wikispecies": "specieswiki",
    "incubator": "incubatorwiki",
    "betawikiversity": "betawikiversity",
    "wmf": "foundationwiki",
    "foundation": "foundationwiki",
    "wikimedia": "foundationwiki",
    "f": "wikifunctionswiki",
    "wikifunctions": "wikifunctionswiki",
    "wikitech": "wikitechwiki",
    "strategy": "strategywiki",
    "testwiki": "testwiki",
}


FAMILY_LANGUAGE_ALIASES = {
    ("wikiversity", "mul"): "betawikiversity",
}


# small bootstrap of Wikimedia global interwiki prefixes whose targets are
# wikimedia wikis. this is fallback prefix metadata only; explicit live
# interwiki metadata loaded by MetadataStore replaces/extends it.
WIKIMEDIA_GLOBAL_WIKI_PREFIXES = {
    "arbcom-zh": ("https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1", "arbcom_zhwiki"),
    "abstract": ("https://abstract.wikipedia.org/wiki/$1", "abstractwiki"),
    "advisory": ("https://advisory.wikimedia.org/wiki/$1", "advisorywiki"),
    "betawikiversity": ("https://beta.wikiversity.org/wiki/$1", "betawikiversity"),
    "nostalgia": ("https://nostalgia.wikipedia.org/wiki/$1", "nostalgiawiki"),
    "tenwiki": ("https://ten.wikipedia.org/wiki/$1", "tenwiki"),
    "test2wiki": ("https://test2.wikipedia.org/wiki/$1", "test2wiki"),
    "testcommons": ("https://test-commons.wikimedia.org/wiki/$1", "testcommonswiki"),
    "testwikidata": ("https://test.wikidata.org/wiki/$1", "testwikidatawiki"),
    "wm2005": ("https://wikimania2005.wikimedia.org/wiki/$1", "wikimania2005wiki"),
    "wm2006": ("https://wikimania2006.wikimedia.org/wiki/$1", "wikimania2006wiki"),
    "wm2007": ("https://wikimania2007.wikimedia.org/wiki/$1", "wikimania2007wiki"),
    "wm2008": ("https://wikimania2008.wikimedia.org/wiki/$1", "wikimania2008wiki"),
    "wm2009": ("https://wikimania2009.wikimedia.org/wiki/$1", "wikimania2009wiki"),
    "wm2010": ("https://wikimania2010.wikimedia.org/wiki/$1", "wikimania2010wiki"),
    "wm2011": ("https://wikimania2011.wikimedia.org/wiki/$1", "wikimania2011wiki"),
    "wm2012": ("https://wikimania2012.wikimedia.org/wiki/$1", "wikimania2012wiki"),
    "wm2013": ("https://wikimania2013.wikimedia.org/wiki/$1", "wikimania2013wiki"),
    "wm2014": ("https://wikimania2014.wikimedia.org/wiki/$1", "wikimania2014wiki"),
    "wm2015": ("https://wikimania2015.wikimedia.org/wiki/$1", "wikimania2015wiki"),
    "wm2016": ("https://wikimania2016.wikimedia.org/wiki/$1", "wikimania2016wiki"),
    "wm2017": ("https://wikimania2017.wikimedia.org/wiki/$1", "wikimania2017wiki"),
    "wm2018": ("https://wikimania2018.wikimedia.org/wiki/$1", "wikimania2018wiki"),
    "wmteam": ("https://wikimaniateam.wikimedia.org/wiki/$1", "wikimaniateamwiki"),
    "wmania": ("https://wikimania.wikimedia.org/wiki/$1", "wikimaniawiki"),
}

SERVICE_PREFIXES = {
    "phab": dict(hostname="phabricator.wikimedia.org", name="Phabricator", destination_type="service", url="https://phabricator.wikimedia.org/$1"),
    "phabricator": dict(hostname="phabricator.wikimedia.org", name="Phabricator", destination_type="service", url="https://phabricator.wikimedia.org/$1"),
    "bugzilla": dict(hostname="bugzilla.wikimedia.org", name="Bugzilla", destination_type="service", url="https://bugzilla.wikimedia.org/show_bug.cgi?id=$1"),
    "mediazilla": dict(hostname="bugzilla.wikimedia.org", name="Bugzilla", destination_type="service", url="https://bugzilla.wikimedia.org/show_bug.cgi?id=$1"),
    "gerrit": dict(hostname="gerrit.wikimedia.org", name="Gerrit", destination_type="service", url="https://gerrit.wikimedia.org/$1"),
    "tools": dict(hostname="toolforge.org", name="Toolforge", destination_type="tool", url="https://toolforge.org/$1"),
    "toolforge": dict(hostname="toolforge.org", name="Toolforge", destination_type="tool", url="https://toolforge.org/$1"),
    "tswiki": dict(hostname="wikitech.wikimedia.org", name="Toolforge wiki", destination_type="service", url="https://wikitech.wikimedia.org/wiki/$1"),
    "sulutil": dict(hostname="meta.wikimedia.org", name="SUL utility", destination_type="service", url="https://meta.wikimedia.org/wiki/Special:CentralAuth/$1"),
    "mail": dict(hostname="lists.wikimedia.org", name="Wikimedia mailing lists", destination_type="service", url="https://lists.wikimedia.org/$1"),
    "mailarchive": dict(hostname="lists.wikimedia.org", name="Wikimedia mailing list archives", destination_type="service", url="https://lists.wikimedia.org/pipermail/$1"),
    "outreach": dict(hostname="outreach.wikimedia.org", name="Outreach wiki", destination_type="service", url="https://outreach.wikimedia.org/wiki/$1"),
    "otrs": dict(hostname="ticket.wikimedia.org", name="Volunteer Response Team", destination_type="service", url="https://ticket.wikimedia.org/otrs/index.pl?Action=AgentTicketZoom&TicketNumber=$1"),
    "otrswiki": dict(hostname="vrt-wiki.wikimedia.org", name="OTRS wiki", destination_type="service", url="https://vrt-wiki.wikimedia.org/wiki/$1"),
    "quality": dict(hostname="quality.wikimedia.org", name="Wikimedia quality initiative", destination_type="service", url="https://quality.wikimedia.org/wiki/$1"),
    "spcom": dict(hostname="spcom.wikimedia.org", name="Wikimedia Ombuds/spam commission", destination_type="service", url="https://spcom.wikimedia.org/wiki/$1"),
    "ticket": dict(hostname="ticket.wikimedia.org", name="Wikimedia ticketing system", destination_type="service", url="https://ticket.wikimedia.org/otrs/index.pl?Action=AgentTicketZoom&TicketNumber=$1"),
    "svn": dict(hostname="svn.wikimedia.org", name="Wikimedia Subversion", destination_type="service", url="https://svn.wikimedia.org/$1"),
    "rev": dict(hostname="www.mediawiki.org", name="MediaWiki revision service", destination_type="service", url="https://www.mediawiki.org/wiki/Special:Code/MediaWiki/$1"),
    "wmania": dict(hostname="wikimania.wikimedia.org", name="Wikimania", destination_type="service", url="https://wikimania.wikimedia.org/wiki/$1"),
    "wm2016": dict(hostname="wikimania2016.wikimedia.org", name="Wikimania 2016", destination_type="service", url="https://wikimania2016.wikimedia.org/wiki/$1"),
    "wm2017": dict(hostname="wikimania2017.wikimedia.org", name="Wikimania 2017", destination_type="service", url="https://wikimania2017.wikimedia.org/wiki/$1"),
    "download": dict(hostname="releases.wikimedia.org", name="Wikimedia releases", destination_type="service", url="https://releases.wikimedia.org/$1"),
    "dbdump": dict(hostname="dumps.wikimedia.org", name="Wikimedia database dumps", destination_type="service", url="https://dumps.wikimedia.org/$1"),
}

CHAPTER_PREFIXES = {
    "wmar": "Wikimedia Argentina", "wmau": "Wikimedia Australia", "wmat": "Wikimedia Austria", "wmbd": "Wikimedia Bangladesh",
    "wmbe": "Wikimedia Belgium", "wmbr": "Wikimedia Brasil", "wmca": "Wikimedia Canada", "wmcz": "Wikimedia Czech Republic",
    "wmdk": "Wikimedia Danmark", "wmde": "Wikimedia Deutschland", "wmfi": "Wikimedia Suomi", "wmhk": "Wikimedia Hong Kong",
    "wmhu": "Wikimedia Hungary", "wmin": "Wikimedia India", "wmke": "Wikimedia Kenya", "wmid": "Wikimedia Indonesia", "wmil": "Wikimedia Israel",
    "wmit": "Wikimedia Italia", "wmnl": "Wikimedia Nederland", "wmmk": "Wikimedia Macedonia", "wmno": "Wikimedia Norge",
    "wmpl": "Wikimedia Polska", "wmru": "Wikimedia Russia", "wmrs": "Wikimedia Srbije", "wmes": "Wikimedia Espana",
    "wmse": "Wikimedia Sverige", "wmch": "Wikimedia CH", "wmph": "Wiki Society of the Philippines", "wmtw": "Wikimedia Taiwan", "wmua": "Wikimedia Ukraine", "wmuk": "Wikimedia UK", "wmza": "Wikimedia South Africa",
}

CHAPTER_FIXED_URLS = {
    "wmhk": "https://meta.wikimedia.org/wiki/Wikimedia_Hong_Kong",
    "wmin": "https://meta.wikimedia.org/wiki/Wikimedia_India",
    "wmke": "https://meta.wikimedia.org/wiki/Wikimedia_Kenya",
    "wmph": "https://meta.wikimedia.org/wiki/Wiki_Society_of_the_Philippines",
    "wmtw": "https://meta.wikimedia.org/wiki/Wikimedia_Taiwan",
    "wmza": "https://meta.wikimedia.org/wiki/Wikimedia_South_Africa",
}

CHAPTER_HOSTS = {
    "wmar": "www.wikimedia.org.ar", "wmau": "wikimedia.org.au", "wmat": "mitglieder.wikimedia.at", "wmbd": "bd.wikimedia.org",
    "wmbe": "be.wikimedia.org", "wmbr": "br.wikimedia.org", "wmca": "ca.wikimedia.org", "wmcz": "www.wikimedia.cz",
    "wmdk": "dk.wikimedia.org", "wmde": "wikimedia.de", "wmfi": "fi.wikimedia.org", "wmke": "meta.wikimedia.org", "wmhk": "meta.wikimedia.org",
    "wmhu": "wikimedia.hu", "wmin": "meta.wikimedia.org", "wmid": "id.wikimedia.org", "wmil": "www.wikimedia.org.il",
    "wmit": "wiki.wikimedia.it", "wmnl": "nl.wikimedia.org", "wmmk": "mk.wikimedia.org", "wmno": "no.wikimedia.org",
    "wmpl": "pl.wikimedia.org", "wmru": "ru.wikimedia.org", "wmrs": "rs.wikimedia.org", "wmes": "www.wikimedia.es",
    "wmse": "se.wikimedia.org", "wmch": "www.wikimedia.ch", "wmph": "meta.wikimedia.org", "wmtw": "meta.wikimedia.org", "wmua": "ua.wikimedia.org", "wmuk": "wikimedia.org.uk", "wmza": "meta.wikimedia.org",
}

COMMON_NAMESPACE_NAMES = frozenset({
    "media", "special", "talk", "user", "user talk", "project", "project talk", "file", "image", "file talk", "image talk",
    "mediawiki", "mediawiki talk", "template", "template talk", "help", "help talk", "category", "category talk", "module", "module talk",
    "portal", "portal talk", "draft", "draft talk", "timedtext", "timedtext talk", "gadget", "gadget talk", "widget", "widget talk",
})

NAMESPACE_ALIASES = {"image": "File", "image talk": "File talk"}

PREFERRED_FAMILY_PREFIX = {
    "wikipedia": "w", "wiktionary": "wikt", "wikinews": "n", "wikibooks": "b", "wikiquote": "q", "wikisource": "s", "wikiversity": "v", "wikivoyage": "voy",
}

SINGLE_WIKI_HOST_ALIASES = {
    "wikidatawiki": ("wikidata.org",),
    "metawiki": ("meta.wikipedia.org",),
    "mediawikiwiki": ("mediawiki.org",),
    "wikifunctionswiki": ("wikifunctions.org",),
}

WIKIMEDIA_PORTAL_HOSTS = {
    "wikipedia.org",
    "www.wikipedia.org",
}

PREFERRED_SERVICE_PREFIX = {
    "Phabricator": "phab",
    "Bugzilla": "bugzilla",
    "Gerrit": "gerrit",
    "Toolforge": "toolforge",
    "Toolforge wiki": "tswiki",
    "SUL utility": "sulutil",
    "Wikimedia mailing lists": "mail",
    "Wikimedia mailing list archives": "mailarchive",
    "Outreach wiki": "outreach",
    "Volunteer Response Team": "otrs",
    "OTRS wiki": "otrswiki",
    "Wikimedia quality initiative": "quality",
    "Wikimedia Subversion": "svn",
    "MediaWiki revision service": "rev",
    "Wikimania": "wmania",
    "Wikimedia releases": "download",
    "Wikimedia database dumps": "dbdump",
}

PREFERRED_SINGLE_WIKI_PREFIX = {
    "commonswiki": "c", "wikidatawiki": "d", "metawiki": "m", "mediawikiwiki": "mw", "specieswiki": "species", "incubatorwiki": "incubator",
    "foundationwiki": "wmf", "wikifunctionswiki": "f", "wikitechwiki": "wikitech", "strategywiki": "strategy", "testwiki": "testwiki",
}


def _build_wikis() -> dict[str, WikiInfo]:
    wikis: dict[str, WikiInfo] = {}
    for family, langs in BOOTSTRAP_LANGS_BY_FAMILY.items():
        data = MULTILINGUAL_FAMILIES[family]
        for lang in langs:
            dbname = f"{lang}{data['suffix']}"
            wikis[dbname] = WikiInfo(
                dbname=dbname,
                family=family,
                project=data["project"],
                language=lang,
                language_name=LANGUAGES.get(lang, lang),
                hostname=f"{lang}.{family}.org",
                site_code=data["site_code"],
                is_multilingual=False,
                is_standard_project=True,
            )
    for dbname, data in SINGLE_WIKIS.items():
        wikis[dbname] = WikiInfo(
            dbname=dbname,
            family=data["family"],
            project=data["project"],
            language=data["language"],
            language_name=LANGUAGES.get(data["language"], data["language"]),
            hostname=data["hostname"],
            sitename=data.get("sitename"),
            is_multilingual=data["language"] == "mul",
            is_standard_project=False,
        )
    return wikis


WIKIS = _build_wikis()
MULTILINGUAL_FAMILY_NAMES = frozenset(MULTILINGUAL_FAMILIES)
