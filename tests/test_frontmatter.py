"""Tests for the frontmatter parser."""

from docket.frontmatter import parse_frontmatter


def test_valid_frontmatter():
    markdown = """---
title: My Document
author: John Doe
---
# Content

This is the content.
"""
    metadata, content = parse_frontmatter(markdown)
    assert metadata == {"title": "My Document", "author": "John Doe"}
    assert content.strip() == "# Content\n\nThis is the content."


def test_missing_frontmatter():
    markdown = "# Just a title\n\nSome content."
    metadata, content = parse_frontmatter(markdown)
    assert metadata == {}
    assert content == markdown


def test_malformed_no_closing_delimiter():
    markdown = """---
title: Missing closing
# Content
"""
    metadata, content = parse_frontmatter(markdown)
    # Should treat as no frontmatter because no closing delimiter
    assert metadata == {}
    assert content == markdown


def test_malformed_empty_value():
    markdown = """---
title:
author: Jane
---
Content
"""
    metadata, content = parse_frontmatter(markdown)
    assert metadata == {"title": "", "author": "Jane"}
    assert content.strip() == "Content"


def test_malformed_line_without_colon():
    markdown = """---
title: Something
Just a line
author: Me
---
Content
"""
    metadata, content = parse_frontmatter(markdown)
    # The line without colon should be ignored
    assert metadata == {"title": "Something", "author": "Me"}
    assert content.strip() == "Content"


def test_frontmatter_with_blank_lines():
    markdown = """---

title: Blank lines

author: Author

---
Content
"""
    metadata, content = parse_frontmatter(markdown)
    assert metadata == {"title": "Blank lines", "author": "Author"}
    assert content.strip() == "Content"


def test_content_preserves_newlines():
    markdown = """---
title: Test
---
Line 1

Line 2
"""
    _, content = parse_frontmatter(markdown)
    assert content == "Line 1\n\nLine 2"

def test_crlf_line_endings():
    markdown = "---\r\ntitle: Windows\r\n---\r\nBody\r\n"
    metadata, content = parse_frontmatter(markdown)
    assert metadata == {"title": "Windows"}
    assert content == "Body"


def test_quoted_values_are_unquoted():
    markdown = '---\ntitle: "Quoted: title"\nname: \'single\'\n---\nx'
    metadata, _ = parse_frontmatter(markdown)
    assert metadata == {"title": "Quoted: title", "name": "single"}


def test_comment_lines_are_ignored():
    metadata, _ = parse_frontmatter("---\n# note\ntitle: A\n---\nx")
    assert metadata == {"title": "A"}


def test_value_may_contain_colon():
    metadata, _ = parse_frontmatter("---\nurl: http://example.com:8080/x\n---\nx")
    assert metadata == {"url": "http://example.com:8080/x"}


def test_byte_order_mark_is_tolerated():
    metadata, content = parse_frontmatter("﻿---\ntitle: A\n---\nbody")
    assert metadata == {"title": "A"}
    assert content == "body"
