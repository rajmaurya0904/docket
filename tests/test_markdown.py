"""Tests for the Markdown compiler."""

import pytest

from docket.markdown import parse, plain_text, render, render_inline, slugify


def html_of(text: str) -> str:
    return render(text).html


def test_heading_levels_and_ids() -> None:
    out = html_of("# One\n\n## Two words\n\n###### Six")
    assert '<h1 id="one">One ' in out
    assert '<h2 id="two-words">Two words ' in out
    assert '<h6 id="six">Six ' in out


def test_duplicate_headings_get_unique_ids() -> None:
    result = render("## Same\n\n## Same\n\n## Same")
    assert [h.id for h in result.headings] == ["same", "same-1", "same-2"]


def test_headings_are_collected_with_plain_text() -> None:
    result = render("# The `docket` **tool**")
    assert [(h.level, h.text) for h in result.headings] == [(1, "The docket tool")]


def test_atx_closing_hashes_are_removed() -> None:
    result = render("## Title ##")
    assert result.headings[0].raw == "Title"


def test_setext_headings() -> None:
    result = render("Title\n=====\n\nSub\n---\n")
    assert [(h.level, h.text) for h in result.headings] == [(1, "Title"), (2, "Sub")]


def test_paragraphs_split_on_blank_lines() -> None:
    assert html_of("one\ntwo\n\nthree") == "<p>one\ntwo</p>\n<p>three</p>"


def test_hard_line_break_with_two_trailing_spaces() -> None:
    assert html_of("a  \nb") == "<p>a<br>\nb</p>"


def test_inline_emphasis_forms() -> None:
    out = render_inline("**b** *i* _j_ __c__ ~~s~~")
    assert out == "<strong>b</strong> <em>i</em> <em>j</em> <strong>c</strong> <del>s</del>"


def test_snake_case_is_not_italic() -> None:
    assert render_inline("a snake_case_name here") == "a snake_case_name here"


def test_inline_code_is_escaped_and_not_formatted() -> None:
    assert render_inline("`<b>*x*</b>`") == "<code>&lt;b&gt;*x*&lt;/b&gt;</code>"


def test_text_is_html_escaped() -> None:
    assert render_inline("1 < 2 & 3 > 2") == "1 &lt; 2 &amp; 3 &gt; 2"


def test_backslash_escapes() -> None:
    assert render_inline(r"\*not italic\* and \`tick") == "*not italic* and `tick"


def test_links_with_title_and_formatting() -> None:
    out = render_inline('see [the **docs**](/a/b "Title")')
    assert out == 'see <a href="/a/b" title="Title">the <strong>docs</strong></a>'


def test_link_urls_are_not_mangled_by_emphasis() -> None:
    assert render_inline("[x](/a_b_c/d_e)") == '<a href="/a_b_c/d_e">x</a>'


def test_link_rewriter_is_applied_to_links_and_images() -> None:
    out = render_inline("[a](x.md) ![b](y.png)", rewrite=lambda u: "/base/" + u)
    assert 'href="/base/x.md"' in out
    assert 'src="/base/y.png"' in out


def test_image_alt_and_autolink() -> None:
    out = render_inline("![logo](l.png) <https://example.com>")
    assert '<img src="l.png" alt="logo">' in out
    assert '<a href="https://example.com">https://example.com</a>' in out


def test_code_link_nesting() -> None:
    assert render_inline("[`run`](/x)") == '<a href="/x"><code>run</code></a>'


def test_fenced_code_keeps_language_and_escapes() -> None:
    out = html_of("```json\n{\"a\": \"<b>\"}\n```")
    assert out == '<pre><code class="language-json">{"a": "&lt;b&gt;"}</code></pre>'


def test_fence_content_is_not_parsed_as_markdown() -> None:
    out = html_of("```\n# not a heading\n- not a list\n```")
    assert "<h1" not in out and "<li>" not in out


def test_unterminated_fence_runs_to_end_of_document() -> None:
    out = html_of("```py\nx = 1\ny = 2")
    assert "x = 1\ny = 2</code>" in out


def test_tilde_fence_and_longer_closing_fence() -> None:
    out = html_of("~~~\na\n~~~~")
    assert "<pre><code>a</code></pre>" == out


def test_indented_code_block() -> None:
    assert html_of("    a = 1\n    b = 2") == "<pre><code>a = 1\nb = 2</code></pre>"


def test_unordered_list_with_nesting() -> None:
    out = html_of("- a\n- b\n  - c\n  - d\n- e")
    assert out == (
        "<ul>\n<li>a</li>\n<li>b\n<ul>\n<li>c</li>\n<li>d</li>\n</ul></li>\n<li>e</li>\n</ul>"
    )


def test_ordered_list_start_number() -> None:
    out = html_of("3. three\n4. four")
    assert out.startswith('<ol start="3">')


def test_loose_list_wraps_items_in_paragraphs() -> None:
    out = html_of("- a\n\n- b")
    assert "<li><p>a</p></li>" in out


def test_task_list() -> None:
    out = html_of("- [x] done\n- [ ] todo")
    assert '<li><input type="checkbox" disabled checked> done</li>' in out
    assert '<li><input type="checkbox" disabled> todo</li>' in out


def test_code_block_inside_list_item() -> None:
    out = html_of("1. Run:\n\n   ```sh\n   docket build\n   ```\n2. Done")
    assert '<code class="language-sh">docket build</code>' in out
    assert out.count("<li>") == 2


def test_blockquote_contains_blocks() -> None:
    out = html_of("> # Title\n> text *here*")
    assert out.startswith("<blockquote>")
    assert "<h1" in out and "<em>here</em>" in out


def test_table_with_alignment_and_escaped_pipe() -> None:
    out = html_of("| a | b | c |\n|:--|:-:|--:|\n| 1 | 2 | x \\| y |")
    assert '<th style="text-align:left">a</th>' in out
    assert '<th style="text-align:center">b</th>' in out
    assert '<td style="text-align:right">x | y</td>' in out


def test_table_pads_short_rows() -> None:
    out = html_of("a | b\n--|--\n1")
    assert "<td>1</td><td></td>" in out


def test_horizontal_rules() -> None:
    assert html_of("---") == "<hr>"
    assert html_of("* * *") == "<hr>"


def test_raw_html_block_passes_through() -> None:
    assert html_of('<div class="note">\nhi\n</div>') == '<div class="note">\nhi\n</div>'


def test_crlf_input() -> None:
    assert html_of("# A\r\n\r\ntext\r\n").count("\r") == 0


def test_empty_input_renders_nothing() -> None:
    assert html_of("") == ""
    assert parse("\n\n") == []


@pytest.mark.parametrize(
    ("text", "slug"),
    [("GET /users", "get-users"), ("Hello, World!", "hello-world"), ("  a  b ", "a-b"), ("", "")],
)
def test_slugify(text: str, slug: str) -> None:
    assert slugify(text) == slug


def test_plain_text_strips_markup() -> None:
    assert plain_text("**a** [b](/c) `d`") == "a b d"
