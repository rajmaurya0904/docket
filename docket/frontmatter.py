"""Frontmatter parser for docket."""

def parse_frontmatter(markdown: str):
    """Parse YAML-like frontmatter from markdown string.

    Returns a tuple (metadata_dict, content_string).
    If no valid frontmatter is found, returns ({}, markdown).
    """
    # Check if markdown starts with a frontmatter delimiter
    if not markdown.startswith('---\n'):
        return {}, markdown

    # Find the closing delimiter
    lines = markdown.splitlines()
    # We already know the first line is '---'
    # Look for the next line that is exactly '---' (after possible whitespace?)
    # According to common spec, the closing delimiter must be on its own line.
    closing_index = -1
    for i, line in enumerate(lines[1:], start=1):  # start after first line
        if line.strip() == '---':
            closing_index = i
            break

    if closing_index == -1:
        # No closing delimiter, treat as no frontmatter
        return {}, markdown

    # Extract frontmatter text (between the delimiters, exclusive)
    frontmatter_lines = lines[1:closing_index]
    # The content is everything after the closing delimiter line
    content_lines = lines[closing_index+1:]
    content = '\n'.join(content_lines)

    # Parse frontmatter lines into a dict
    metadata = {}
    for line in frontmatter_lines:
        # Skip empty lines
        if not line.strip():
            continue
        # Split on first colon
        if ':' not in line:
            # If no colon, maybe ignore or treat as key with empty value?
            # We'll ignore for simplicity.
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        metadata[key] = value

    return metadata, content