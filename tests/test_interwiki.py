from wmlinksfromhell.models import DestinationType, InterwikiEntry, ResolutionStatus

def test_local_link_with_source(resolver):
    result = resolver.resolve_interwiki("Apple", source="enwiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "Apple"
    assert result.syntax_type.value == "local_wikilink"


def test_local_link_without_source_still_parses_but_has_no_dbname(resolver):
    result = resolver.resolve_interwiki("Apple")
    assert result.destination.dbname is None
    assert result.destination.title == "Apple"


def test_short_project_shortcut_with_language(resolver):
    result = resolver.resolve_interwiki(":w:en:Apple")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "Apple"


def test_long_form_project_prefix(resolver):
    result = resolver.resolve_interwiki(":wikipedia:de:Beispiel")
    assert result.destination.dbname == "dewiki"
    assert result.destination.title == "Beispiel"

def test_long_form_project_prefix_is_fixed_english_without_language(resolver):
    for prefix, expected in (
        ("wikipedia", "enwiki"),
        ("wiktionary", "enwiktionary"),
        ("wikibooks", "enwikibooks"),
        ("wikiquote", "enwikiquote"),
        ("wikinews", "enwikinews"),
        ("wikisource", "enwikisource"),
        ("wikiversity", "enwikiversity"),
        ("wikivoyage", "enwikivoyage"),
    ):
        result = resolver.resolve_interwiki(f"{prefix}:Main Page", source="dewiki")
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.dbname == expected



def test_project_prefix_uses_documented_source_language_for_other_family(resolver):
    for source, prefix, expected in (
        ("dewiki", "b", "dewikibooks"),
        ("dewiki", "q", "dewikiquote"),
        ("itwiki", "b", "itwikibooks"),
        ("frwiki", "wikt", "frwiktionary"),
        ("simplewiki", "b", "simplewikibooks"),
    ):
        result = resolver.resolve_interwiki(f":{prefix}:Main Page", source=source)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.dbname == expected


def test_same_family_project_shortcut_uses_english_project(resolver):
    for source, prefix, expected in (
        ("dewiki", "w", "enwiki"),
        ("dewiktionary", "wikt", "enwiktionary"),
        ("dewikiquote", "q", "enwikiquote"),
    ):
        result = resolver.resolve_interwiki(f":{prefix}:Main Page", source=source)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.dbname == expected


def test_project_prefix_on_multilingual_sources_uses_english_project(resolver):
    for source, prefix, expected in (
        ("metawiki", "b", "enwikibooks"),
        ("commonswiki", "q", "enwikiquote"),
        ("mulwikisource", "n", "enwikinews"),
    ):
        result = resolver.resolve_interwiki(f":{prefix}:Main Page", source=source)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.dbname == expected


def test_project_prefix_without_source_is_still_resolvable(resolver):
    result = resolver.resolve_interwiki(":w:Apple")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"


def test_language_only_prefix_from_family_source(resolver):
    # without the leading colon, a language-only target is an interlanguage link
    result = resolver.resolve_interwiki("en:Apple", source="dewiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"


def test_language_only_prefix_from_meta_defaults_to_wikipedia(resolver):
    result = resolver.resolve_interwiki(":pl:2006", source="metawiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "plwiki"
    assert result.destination.title == "2006"


def test_leading_colon_language_only_link_keeps_the_same_destination(resolver):
    result = resolver.resolve_interwiki(":en:Apple", source="dewiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "Apple"


def test_leading_colon_does_not_disable_explicit_project_chain(resolver):
    result = resolver.resolve_interwiki(":de:q:Hauptseite", source="metawiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "dewikiquote"
    assert result.destination.title == "Hauptseite"


def test_documented_left_to_right_chain_via_meta(resolver):
    result = resolver.resolve_interwiki(":m:en:About", source="metawiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "About"


def test_documented_language_then_same_family_project_reaches_english_wikipedia(resolver):
    result = resolver.resolve_interwiki(":pl:w:2006", source="metawiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "2006"


def test_documented_sister_project_chain_keeps_source_language(resolver):
    result = resolver.resolve_interwiki(":w:it:b:Wiskunde", source="metawiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "itwikibooks"
    assert result.destination.title == "Wiskunde"

def test_language_only_prefix_without_source_is_ambiguous(resolver):
    result = resolver.resolve_interwiki(":en:Apple")
    assert result.status is ResolutionStatus.CONTEXT_REQUIRED


def test_single_wiki_prefix_commons(resolver):
    result = resolver.resolve_interwiki(":c:File:Example.jpg")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "commonswiki"
    assert result.destination.namespace == "File"
    assert result.destination.title == "Example.jpg"


def test_single_wiki_prefix_wikidata(resolver):
    result = resolver.resolve_interwiki(":d:Q42")
    assert result.destination.dbname == "wikidatawiki"
    assert result.destination.title == "Q42"


def test_portable_form_project_language_page(resolver):
    result = resolver.resolve_interwiki(":s:mul:Page")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "mulwikisource"
    assert result.destination.title == "Page"


def test_reversed_language_project_order(resolver):
    # discouraged per wikimedia docs, but should still resolve
    result = resolver.resolve_interwiki(":de:q:Hauptseite")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "dewikiquote"
    assert result.destination.title == "Hauptseite"


def test_namespace_is_not_mistaken_for_interwiki_prefix(resolver):
    result = resolver.resolve_interwiki("Help:Contents", source="enwiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.namespace == "Help"
    assert result.destination.title == "Contents"
    assert result.destination.dbname == "enwiki"


def test_file_namespace_colon_is_not_an_interwiki_separator(resolver):
    result = resolver.resolve_interwiki("File:Example.jpg", source="enwiki")
    assert result.destination.namespace == "File"
    assert result.destination.title == "Example.jpg"


def test_title_with_colon_after_project_language(resolver):
    result = resolver.resolve_interwiki(":w:en:Help:Contents")
    assert result.destination.dbname == "enwiki"
    assert result.destination.namespace == "Help"
    assert result.destination.title == "Contents"


def test_chapter_prefix_points_to_meta_organization_page(resolver):
    result = resolver.resolve_interwiki("wmin")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.destination_type is DestinationType.ORGANIZATION
    assert result.destination.dbname == "metawiki"
    assert result.destination.title == "Wikimedia India"


def test_service_prefix_is_not_a_wiki(resolver):
    result = resolver.resolve_interwiki("phab:T12345")
    assert result.destination.destination_type is DestinationType.SERVICE
    assert result.destination.dbname is None
    assert result.destination.hostname == "phabricator.wikimedia.org"


def test_unknown_prefix_falls_back_to_local_title(resolver):
    # "notaprefix" matches nothing, so the whole thing is a local title
    result = resolver.resolve_interwiki("notaprefix:Something", source="enwiki")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "notaprefix:Something" or result.destination.namespace


def test_fragment_preserved_through_interwiki_resolution(resolver):
    result = resolver.resolve_interwiki(":w:en:Apple#History")
    assert result.destination.title == "Apple"
    assert result.destination.fragment == "History"


def test_malformed_empty_target(resolver):
    result = resolver.resolve_interwiki("")
    assert result.status is ResolutionStatus.MALFORMED


def test_metadata_missing_for_unbootstrapped_family_language(resolver):
    # Korean is known globally, but this fixture does not bootstrap a Korean Wikinews wiki.
    result = resolver.resolve_interwiki(":n:ko:Foo")
    assert result.status is ResolutionStatus.METADATA_MISSING


def test_language_prefix_without_source_requires_context(resolver):
    result = resolver.resolve_interwiki("en:Apple")
    assert result.status is ResolutionStatus.CONTEXT_REQUIRED


def test_language_project_order_resolves_without_source(resolver):
    result = resolver.resolve_interwiki(":de:q:Hauptseite")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "dewikiquote"
    assert result.prefix_kind == "language_project"


def test_project_language_chain_exposes_prefix_metadata(resolver):
    result = resolver.resolve_interwiki(":w:en:Apple")
    assert result.prefix == "w:en"
    assert result.canonical_prefix == "w:en"
    assert result.prefix_kind == "language_project"
    assert result.is_project_prefix
    assert result.is_language_prefix
    assert result.is_language_project


def test_single_wiki_prefix_has_canonical_shortcut(resolver):
    result = resolver.resolve_interwiki(":meta:Main_Page")
    assert result.destination.dbname == "metawiki"
    assert result.canonical_prefix == "m"


def test_meta_then_language_then_title_matches_documented_chain(resolver):
    result = resolver.resolve_interwiki(":m:en:About")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "enwiki"
    assert result.destination.title == "About"


def test_fixed_organization_prefix_resolves_without_inventing_a_target(resolver, metadata):
    metadata._global_interwikis["wmin"] = InterwikiEntry(
        prefix="wmin",
        url="https://meta.wikimedia.org/wiki/Wikimedia_India",
        destination_dbname="metawiki",
        destination_type=DestinationType.ORGANIZATION,
    )
    result = resolver.resolve_interwiki("wmin")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.destination_type is DestinationType.ORGANIZATION
    assert resolver.to_interwiki(result.destination) == "wmin"


def test_fixed_prefix_cannot_take_an_arbitrary_title(resolver, metadata):
    metadata._global_interwikis["wmin"] = InterwikiEntry(
        prefix="wmin",
        url="https://meta.wikimedia.org/wiki/Wikimedia_India",
        destination_dbname="metawiki",
        destination_type=DestinationType.ORGANIZATION,
    )
    result = resolver.resolve_interwiki("wmin:Other")
    assert result.status is ResolutionStatus.UNSUPPORTED


def test_fixed_chapter_prefixes_do_not_accept_arbitrary_titles(resolver):
    for prefix in ("wmhk", "wmin", "wmke", "wmph", "wmtw", "wmza"):
        result = resolver.resolve_interwiki(prefix)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.destination_type is DestinationType.ORGANIZATION
        assert resolver.to_interwiki(result.destination) == prefix
        assert resolver.resolve_interwiki(prefix + ":Other").status is ResolutionStatus.UNSUPPORTED


def test_dynamic_chapter_prefix_uses_chapter_hostname(resolver):
    result = resolver.resolve_interwiki("wmde:Foo")
    assert result.destination.destination_type is DestinationType.ORGANIZATION
    assert result.destination.dbname is None
    assert result.destination.hostname == "wikimedia.de"
    assert resolver.to_url(result.destination) == "https://wikimedia.de/wiki/Foo"


def test_fixed_chapter_destination_keeps_its_prefix_identity(resolver):
    for prefix in ("wmin", "wmhk", "wmke", "wmph", "wmtw", "wmza"):
        result = resolver.resolve_interwiki(prefix)
        assert result.destination.organization_name == prefix
        assert resolver.to_interwiki(result.destination) == prefix


def test_newer_chapter_prefixes_from_bootstrap_are_recognized(resolver):
    for prefix, host in (("wmke", "meta.wikimedia.org"), ("wmph", "meta.wikimedia.org"), ("wmza", "meta.wikimedia.org")):
        result = resolver.resolve_interwiki(prefix)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.destination_type is DestinationType.ORGANIZATION
        assert result.destination.organization_name == prefix
        assert resolver.to_interwiki(result.destination) == prefix


def test_beta_wikiversity_documented_short_form_works(resolver):
    result = resolver.resolve_interwiki("v:mul:Foo")
    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "betawikiversity"
    assert result.destination.hostname == "beta.wikiversity.org"


def test_fixed_chapter_urls_are_not_reinterpreted_as_meta_pages(resolver):
    for prefix in ("wmin", "wmhk", "wmke", "wmph", "wmtw", "wmza"):
        result = resolver.resolve_interwiki(prefix)
        assert result.destination.destination_type is DestinationType.ORGANIZATION
        assert result.destination.dbname == "metawiki"
        assert result.destination.organization_name == prefix
        assert result.canonical_interwiki == prefix


def test_noc_language_aliases_resolve_after_metadata_refresh(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo

    metadata._wikis.update({
        "simplewiki": WikiInfo("simplewiki", "wikipedia", "wikipedia", "en", "Simple English", "simple.wikipedia.org", is_standard_project=True),
        "zhwiki": WikiInfo("zhwiki", "wikipedia", "wikipedia", "zh", "Chinese", "zh.wikipedia.org"),
    })
    metadata._reindex()
    text = """<?php
    return [
        '_wiki:simple' => '1 https://simple.wikipedia.org/wiki/$1',
        '_wiki:en-simple' => '1 https://simple.wikipedia.org/wiki/$1',
        '_wiki:cmn' => '1 https://zh.wikipedia.org/wiki/$1',
        '_wiki:zh-cn' => '1 https://zh.wikipedia.org/wiki/$1',
    ];
    """
    aliases, prefixes = metadata._parse_family_language_entries(text)
    metadata._family_language_aliases.update(aliases)
    metadata._family_language_prefixes.update(prefixes)

    assert resolver.resolve_interwiki("w:en-simple:Foo").destination.dbname == "simplewiki"
    assert resolver.resolve_interwiki("w:cmn:Foo").destination.dbname == "zhwiki"
    assert resolver.resolve_interwiki("w:zh-cn:Foo").destination.dbname == "zhwiki"
    assert resolver.resolve_interwiki("w:en-simple:Foo").canonical_interwiki == "w:simple:Foo"


def test_beta_wikiversity_alias_mul_is_canonical(resolver):
    result = resolver.resolve_interwiki("v:mul:Foo")
    assert result.destination.dbname == "betawikiversity"
    assert result.canonical_interwiki == "betawikiversity:Foo"




def test_known_family_language_beats_conflicting_global_prefix(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, WikiInfo

    cases = (
        ("bhwiki", "wikipedia", "bho"),
        ("cbk_zamwiki", "wikipedia", "cbk"),
        ("emlwiki", "wikipedia", "egl"),
        ("map_bmswiki", "wikipedia", "jv-x-bms"),
        ("nowiki", "wikipedia", "nb"),
        ("nrmwiki", "wikipedia", "nrf"),
        ("roa_tarawiki", "wikipedia", "nap-x-tara"),
        ("shywiktionary", "wiktionary", "shy-latn"),
    )

    for dbname, family, language in cases:
        metadata._wikis[dbname] = WikiInfo(
            dbname, family, family, language, language, f"{language}.{family}.org",
            is_standard_project=True,
        )
        metadata._reindex()
        metadata._global_interwikis[language] = InterwikiEntry(
            prefix=language,
            url="https://en.wikipedia.org/wiki/$1",
            destination_dbname="enwiki",
            destination_type=DestinationType.WIKI,
        )

        target = f"wikt:{language}:Main Page" if family == "wiktionary" else f"{language}:Main Page"
        result = resolver.resolve_interwiki(target, source="metawiki")

        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.dbname == dbname
        assert result.canonical_interwiki == (f"wikt:{language}:Main Page" if family == "wiktionary" else f"w:{language}:Main Page")


def test_sitematrix_language_beats_conflicting_family_alias(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, WikiInfo

    metadata._wikis["simplewikibooks"] = WikiInfo(
        "simplewikibooks", "wikibooks", "wikibooks", "simple", "Simple English",
        "simple.wikibooks.org", is_standard_project=True,
    )
    metadata._reindex()
    metadata._family_language_aliases[("wikibooks", "simple")] = "enwikibooks"
    metadata._global_interwikis["simple"] = InterwikiEntry(
        prefix="simple",
        url="https://en.wikipedia.org/wiki/$1",
        destination_dbname="enwiki",
        destination_type=DestinationType.WIKI,
    )

    result = resolver.resolve_interwiki("b:simple:Main Page", source="metawiki")

    assert result.status is ResolutionStatus.RESOLVED
    assert result.destination.dbname == "simplewikibooks"
    assert result.canonical_interwiki == "b:simple:Main Page"


def test_family_language_alias_beats_conflicting_global_prefix(resolver, metadata):
    from wmlinksfromhell.models import InterwikiEntry, WikiInfo

    cases = (
        ("bhwiki", "bho", "bhwiki"),
        ("cbk_zamwiki", "cbk-zam", "cbk_zamwiki"),
        ("emlwiki", "egl", "emlwiki"),
        ("map_bmswiki", "jv-x-bms", "map_bmswiki"),
        ("nowiki", "nb", "nowiki"),
        ("nrmwiki", "nrf", "nrmwiki"),
        ("roa_tarawiki", "nap-x-tara", "roa_tarawiki"),
        ("shywiktionary", "shy-latn", "shywiktionary"),
    )

    for dbname, prefix, expected in cases:
        family = "wiktionary" if dbname.endswith("wiktionary") else "wikipedia"
        language = prefix
        metadata._wikis[dbname] = WikiInfo(
            dbname, family, family, language, language, f"{prefix}.{family}.org",
            is_standard_project=True,
        )
        metadata._reindex()
        metadata._family_language_aliases[(family, prefix)] = dbname
        metadata._global_interwikis[prefix] = InterwikiEntry(
            prefix=prefix,
            url="https://en.wikipedia.org/wiki/$1",
            destination_dbname="enwiki",
            destination_type=DestinationType.WIKI,
        )

        result = resolver.resolve_interwiki(f"{prefix}:Main Page", source=dbname)

        assert result.status is ResolutionStatus.RESOLVED
        assert result.destination.dbname == expected
        assert result.canonical_interwiki == f"{'wikt' if family == 'wiktionary' else 'w'}:{prefix}:Main Page"


def test_special_and_private_wikis_do_not_get_invented_prefixes(resolver, metadata):
    from wmlinksfromhell.models import WikiInfo, InterwikiEntry, DestinationType

    for dbname, host in (
        ("arbcom_enwiki", "wikipedia-en-arbcom.wikimedia.org"),
        ("arbcom_dewiki", "wikipedia-de-arbcom.wikimedia.org"),
        ("boardwiki", "board.wikimedia.org"),
        ("checkuserwiki", "checkuser.wikimedia.org"),
    ):
        metadata._wikis[dbname] = WikiInfo(dbname, "special", dbname, "en", "English", host, is_standard_project=False)
    metadata._reindex()
    metadata._global_interwikis["arbcom-zh"] = InterwikiEntry(
        "Arbcom-zh", "https://wikipedia-zh-arbcom.wikimedia.org/wiki/$1",
        destination_dbname="arbcom_zhwiki", destination_type=DestinationType.WIKI,
    )

    for dbname in ("arbcom_enwiki", "arbcom_dewiki", "boardwiki", "checkuserwiki"):
        destination = resolver.resolve_url(f"https://{metadata._wikis[dbname].hostname}/wiki/Foo").destination
        assert destination is not None
        with __import__("pytest").raises(Exception):
            resolver.to_interwiki(destination, source="metawiki")


def test_fixed_wiki_prefix_with_unknown_host_does_not_fall_back_to_local(resolver, metadata):
    metadata._global_interwikis["mystery"] = InterwikiEntry(
        prefix="mystery",
        url="https://unknown.wikimedia.org/wiki/Foo",
        destination_type=DestinationType.WIKI,
    )
    result = resolver.resolve_interwiki("mystery")
    assert result.status is ResolutionStatus.METADATA_MISSING
