from src.transform.cleaners import (
    clean_description,
    collapse_whitespace,
    html_to_text,
    remove_boilerplate,
)


def test_collapse_whitespace():
    assert collapse_whitespace("  a\n\n  b\t\tc  ") == "a b c"


def test_html_to_text_strips_tags():
    html = "<ul><li>Lead <b>teams</b></li><li>Ship <i>code</i></li></ul>"
    assert html_to_text(html) == "Lead teams Ship code"


def test_html_to_text_removes_scripts_and_styles():
    html = "<style>.x{}</style><script>bad()</script><p>Good text</p>"
    assert "bad()" not in html_to_text(html)
    assert "Good text" in html_to_text(html)


def test_html_to_text_empty():
    assert html_to_text(None) == ""
    assert html_to_text("") == ""


def test_remove_boilerplate_drops_navigation_lines():
    text = "Careers\nJobs matched\nReal description here."
    cleaned = remove_boilerplate(text)
    assert "Careers" not in cleaned
    assert "Jobs matched" not in cleaned
    assert "Real description" in cleaned


def test_clean_description_merges_and_cleans():
    parts = ["<p>First   paragraph.</p>", None, "<p>Second.</p>"]
    assert clean_description(parts) == "First paragraph. Second."