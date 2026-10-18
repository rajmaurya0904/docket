"""Tests for API endpoint detection."""

import pytest

from docket.api_parser import (
    extract,
    insert_explorers,
    match_signature,
    parse_api_block,
)
from docket.markdown import CodeBlock, RawHtml, parse

SECTION = """# Users

## GET /users/{id}

Fetch one user.

### Parameters

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| id | path | integer | yes | The user id |
| verbose | query | boolean | no | Include extras |

### Response

```json
{ "id": 1 }
```

## POST /users

Create a user.

### Request Body

```json
{ "name": "string" }
```

### Response 201

```json
{ "id": 3 }
```

## Not an endpoint

Text.
"""


def test_match_signature() -> None:
    assert match_signature("GET /users") == ("GET", "/users")
    assert match_signature("`delete` /a/{id}") == ("DELETE", "/a/{id}")
    assert match_signature("Getting started") is None
    assert match_signature("GET users") is None
    assert match_signature("GET /users extra words") is None


def test_heading_sections_become_endpoints() -> None:
    endpoints, placements = extract(parse(SECTION))
    assert [e.signature for e in endpoints] == ["GET /users/{id}", "POST /users"]
    assert len(placements) == 2


def test_summary_is_the_text_before_the_first_subheading() -> None:
    endpoints, _ = extract(parse(SECTION))
    assert endpoints[0].summary == "Fetch one user."


def test_parameter_table_is_read() -> None:
    get = extract(parse(SECTION))[0][0]
    by_name = {p.name: p for p in get.params}
    assert by_name["id"].location == "path" and by_name["id"].required
    assert by_name["id"].type == "integer"
    assert by_name["verbose"].location == "query" and not by_name["verbose"].required
    assert by_name["verbose"].description == "Include extras"


def test_request_body_and_response_status() -> None:
    post = extract(parse(SECTION))[0][1]
    assert post.request_body == '{ "name": "string" }'
    assert [(r.status, r.body) for r in post.responses] == [("201", '{ "id": 3 }')]


def test_response_status_defaults_to_200() -> None:
    get = extract(parse(SECTION))[0][0]
    assert get.responses[0].status == "200"


def test_anchor_matches_heading_id() -> None:
    blocks = parse(SECTION)
    endpoints, _ = extract(blocks)
    assert endpoints[0].anchor == "get-usersid"


def test_section_ends_at_next_heading_of_same_level() -> None:
    _, placements = extract(parse(SECTION))
    blocks = parse(SECTION)
    start, end, _ = placements[0]
    assert blocks[end].raw == "POST /users"  # type: ignore[union-attr]
    assert start < end


def test_undeclared_path_params_are_added() -> None:
    text = "## DELETE /teams/{team}/members/{member}\n\nRemove."
    (endpoint,), _ = extract(parse(text))
    assert [(p.name, p.location, p.required) for p in endpoint.params] == [
        ("team", "path", True),
        ("member", "path", True),
    ]


def test_invalid_json_in_example_produces_a_warning() -> None:
    text = "## GET /x\n\n### Response\n\n```json\n{ nope }\n```\n"
    (endpoint,), _ = extract(parse(text))
    assert len(endpoint.warnings) == 1
    assert "GET /x" in endpoint.warnings[0] and "not valid JSON" in endpoint.warnings[0]


def test_non_json_examples_are_not_validated() -> None:
    text = "## GET /x\n\n### Response\n\n```text\nplain\n```\n"
    (endpoint,), _ = extract(parse(text))
    assert endpoint.warnings == []


def test_unknown_parameter_location_warns_and_falls_back_to_query() -> None:
    text = "## GET /x\n\n### Parameters\n\n| Name | In |\n|--|--|\n| a | cookie |\n"
    (endpoint,), _ = extract(parse(text))
    assert endpoint.params[0].location == "query"
    assert "unknown location" in endpoint.warnings[0]


def test_api_fence_full_syntax() -> None:
    code = """GET /users/{id}
summary: Fetch a user
param id path integer required: The user id
param verbose query boolean: Include extras
header Authorization: Bearer abc
response 200:
  { "id": 1 }
response 404:
  { "error": "not found" }
"""
    endpoint = parse_api_block(code)
    assert endpoint.signature == "GET /users/{id}"
    assert endpoint.summary == "Fetch a user"
    assert endpoint.headers == {"Authorization": "Bearer abc"}
    assert [(p.name, p.location, p.type, p.required) for p in endpoint.params] == [
        ("id", "path", "integer", True),
        ("verbose", "query", "boolean", False),
    ]
    assert [r.status for r in endpoint.responses] == ["200", "404"]
    assert endpoint.responses[1].body == '{ "error": "not found" }'
    assert endpoint.warnings == []


def test_api_fence_body_block_is_dedented() -> None:
    endpoint = parse_api_block('POST /x\nbody:\n  {\n    "a": 1\n  }\n')
    assert endpoint.request_body == '{\n  "a": 1\n}'


def test_api_fence_with_invalid_json_body_warns() -> None:
    endpoint = parse_api_block("POST /x\nbody:\n  {oops\n")
    assert endpoint.warnings and "request body" in endpoint.warnings[0]


@pytest.mark.parametrize(
    "code",
    [
        "",
        "hello world",
        "GET /x\nbogus line",
        "GET /x\nparam id",
        "GET /x\nparam id nowhere string",
        "GET /x\nheader : value",
    ],
)
def test_api_fence_errors(code: str) -> None:
    with pytest.raises(ValueError):
        parse_api_block(code)


def test_extract_wraps_api_block_errors() -> None:
    with pytest.raises(ValueError, match="invalid api block"):
        extract(parse("```api\nnonsense\n```"))


def test_api_fence_is_replaced_by_panel() -> None:
    blocks = parse("Intro\n\n```api\nGET /ping\n```\n\nAfter")
    endpoints, placements = extract(blocks)
    out = insert_explorers(blocks, placements, lambda e: f"<panel {e.signature}>")
    assert any(isinstance(b, RawHtml) and b.html == "<panel GET /ping>" for b in out)
    assert not any(isinstance(b, CodeBlock) for b in out)
    assert len(endpoints) == 1


def test_heading_section_keeps_content_and_gets_panel_after() -> None:
    blocks = parse(SECTION)
    _, placements = extract(blocks)
    out = insert_explorers(blocks, placements, lambda e: f"<panel {e.signature}>")
    html = [b.html for b in out if isinstance(b, RawHtml)]
    assert html == ["<panel GET /users/{id}>", "<panel POST /users>"]
    assert sum(isinstance(b, CodeBlock) for b in out) == 3
    first_panel = next(i for i, b in enumerate(out) if isinstance(b, RawHtml))
    assert isinstance(out[first_panel - 1], CodeBlock)


def test_panel_at_end_of_document() -> None:
    blocks = parse("## GET /last\n\nText")
    _, placements = extract(blocks)
    out = insert_explorers(blocks, placements, lambda e: "<panel>")
    assert isinstance(out[-1], RawHtml)


def test_page_without_endpoints() -> None:
    endpoints, placements = extract(parse("# Hi\n\ntext"))
    assert endpoints == [] and placements == []
