#!/usr/bin/env python3
"""Dependency-free tests for fill_tool_subsections.py.

Run with:  python scripts/test_fill_tool_subsections.py
"""

import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fill_tool_subsections as fts  # noqa: E402

TAB = ("tools", "tools.tsv", "Tools")


def write(path, text):
    path.write_text(textwrap.dedent(text))


MASTER_YML = """\
    id: tools
    title: Community curated tools
    tabs:
    - id: t
      title: T
      content:
      - title_md: alpha
        description_md: desc alpha
      - title_md: beta
        description_md: "beta one\\nbeta two"
      - title_md: "dup title "
        description_md: first occurrence wins
        button_link: http://first
      - title_md: dup title
        description_md: duplicate occurrence
        button_link: http://second
    """

SECTION_YML = """\
    id: lcms
    title: LC/MS data analysis
    tabs:
    - id: overview
      title: Overview
      heading_md: ""
    - id: tools
      title: Tools
      heading_md: Tools
      content:
      - title_md: stale
        description_md: old item that must be gone
    """


def make_env(tmp, master=MASTER_YML, tsv=""):
    sections = tmp / "sections"
    mappings = tmp / "mappings"
    sections.mkdir(parents=True)
    mappings.mkdir()
    write(sections / "_tools.yml", master)
    write(sections / "2_LCMS.yml", SECTION_YML)
    (mappings / "tools.tsv").write_text(tsv)
    return sections, mappings


def run(sections, mappings, tab="tools"):
    return fts.fill_tab(
        tab, sections_dir=sections, mapping_dir=mappings, dry_run=False)


def tab_of(path):
    import yaml
    data = yaml.safe_load(path.read_text())
    return next(t for t in data["tabs"] if t["id"] == "tools")


def test_happy_path():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(
            tmp,
            tsv="name\tsection\tsubsection\n"
                "alpha\tlcms\tstatistics\n"
                "beta\tlcms\tstatistics\n")
        run(sections, mappings)
        tab = tab_of(sections / "2_LCMS.yml")
        assert set(tab["content"]) == {"subsections"}
        subs = tab["content"]["subsections"]
        assert [s["id"] for s in subs] == ["statistics"]
        titles = [i["title_md"] for i in subs[0]["content"]]
        assert titles == ["alpha", "beta"], titles
        assert "stale" not in titles, "old flat items must be removed"
        # multiline description preserved with real newline
        beta = next(i for i in subs[0]["content"] if i["title_md"] == "beta")
        assert "beta one\nbeta two" == beta["description_md"]
    print("test_happy_path OK")


def test_extra_fields_and_duplicate_titles():
    """All item fields (button_*) are copied; duplicates keep first link;
    names match regardless of whitespace differences."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(
            tmp, tsv="name\tsection\tsubsection\n"
                     "dup title\tlcms\tpreprocessing\n")
        run(sections, mappings)
        subs = tab_of(sections / "2_LCMS.yml")["content"]["subsections"]
        item = subs[0]["content"][0]
        assert item["button_link"] == "http://first", item
    print("test_extra_fields_and_duplicate_titles OK")


def test_unknown_item_skipped():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(
            tmp, tsv="name\tsection\tsubsection\n"
                     "ghost\tlcms\tstatistics\n")
        run(sections, mappings)  # warns, does not raise
    print("test_unknown_item_skipped OK")


def test_conflicting_subsection_raises():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(
            tmp, tsv="name\tsection\tsubsection\n"
                     "alpha\tlcms\tstatistics\n"
                     "alpha\tlcms\tpreprocessing\n")
        try:
            run(sections, mappings)
        except ValueError as e:
            assert "only one subsection" in str(e), str(e)
        else:
            raise AssertionError("expected ValueError for conflicting subsection")
    print("test_conflicting_subsection_raises OK")


def test_unknown_section_raises():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(
            tmp, tsv="name\tsection\tsubsection\n"
                     "alpha\tdoesnotexist\tstatistics\n")
        try:
            run(sections, mappings)
        except SystemExit as e:
            assert "unknown section ids" in str(e), str(e)
        else:
            raise AssertionError("expected SystemExit for unknown section")
    print("test_unknown_section_raises OK")


def test_multiline_description_kept():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(
            tmp, tsv="name\tsection\tsubsection\n"
                     "beta\tlcms\tin_silico\n")
        run(sections, mappings)
        text = (sections / "2_LCMS.yml").read_text()
        assert "|-" in text, "multiline desc should use literal block scalar"
        subs = tab_of(sections / "2_LCMS.yml")["content"]["subsections"]
        got = subs[0]["content"][0]["description_md"]
        assert got == "beta one\nbeta two", repr(got)
    print("test_multiline_description_kept OK")


def test_workflows_tab_created_after_overview():
    """A missing tab is created after overview with the right title."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sections, mappings = make_env(tmp)
        write(sections / "_tools.yml", textwrap.dedent("""\
            id: tools
            title: x
            tabs:
            - id: t
              content:
              - title_md: wf one
                description_md: wd
                button_link: http://wf
                button_icon: view
            """))
        fts.TABS["tools"] = ("_tools.yml", "tools.tsv", "Workflows")
        (mappings / "tools.tsv").write_text(
            "name\tsection\tsubsection\nwf one\tlcms\tpreprocessing\n")
        run(sections, mappings)
        import yaml
        data = yaml.safe_load((sections / "2_LCMS.yml").read_text())
        ids = [t["id"] for t in data["tabs"]]
        assert ids == ["overview", "tools"], ids
        tab = next(t for t in data["tabs"] if t["id"] == "tools")
        assert tab["title"] == "Workflows"
        item = tab["content"]["subsections"][0]["content"][0]
        assert item["button_link"] == "http://wf"
        assert item["button_icon"] == "view"
    print("test_workflows_tab_created_after_overview OK")


if __name__ == "__main__":
    test_happy_path()
    test_extra_fields_and_duplicate_titles()
    test_unknown_item_skipped()
    test_conflicting_subsection_raises()
    test_unknown_section_raises()
    test_multiline_description_kept()
    test_workflows_tab_created_after_overview()
    print("\nAll tests passed.")
