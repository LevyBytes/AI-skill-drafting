"""Parse document structure without executing examples or guessing their meaning."""
import re
from collections import Counter
from html.parser import HTMLParser
from markdown_it import MarkdownIt

PARSER = MarkdownIt("commonmark", {"html": True}).enable("table")


def slug(text):
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


class HTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.anchors, self.custom = [], [], []

    def handle_starttag(self, tag, attrs):
        allowed = {"a", "img", "p", "div", "span", "br", "hr", "details", "summary", "table", "tr", "td", "th", "thead", "tbody", "pre", "code", "kbd", "em", "strong", "sup", "sub", "ul", "ol", "li", "blockquote", "video", "source"}
        if tag not in allowed:
            self.custom.append(tag)
        for key, value in attrs:
            if value and key in {"href", "src", "poster"}:
                self.links.append(value)
            if value and key in {"id", "name"}:
                self.anchors.append(value)


def inspect(text):
    tokens = PARSER.parse(text)
    headings, links, anchors, code, units, issues = [], [], set(), [], [], []
    counts = Counter()
    lines = text.splitlines()
    for index, token in enumerate(tokens):
        if token.map and token.level == 0 and token.type not in {"inline", "heading_close"}:
            units.append({"kind": token.type, "start": token.map[0] + 1, "end": token.map[1]})
        if token.type == "heading_open":
            if token.map is None or not (0 <= token.map[0] < token.map[1] <= len(lines)):
                issues.append({"code": "invalid_source_position", "kind": token.type})
                continue
            inline = tokens[index + 1]
            title = "".join(c.content for c in inline.children or [] if c.type in {"text", "code_inline"})
            key = slug(title)
            count = counts[key]
            counts[key] += 1
            anchors.add(key + (f"-{count}" if count else ""))
            headings.append({"title": title, "level": int(token.tag[1:]), "line": token.map[0] + 1})
        if token.type in {"fence", "code_block"}:
            code.append((token.info.strip(), token.content))
            if token.type == "fence":
                if token.map is None or not (0 <= token.map[0] < token.map[1] <= len(lines)):
                    issues.append({"code": "invalid_source_position", "kind": token.type})
                    continue
                last = re.sub(r"^\s*(?:>\s*)+", "", lines[token.map[1] - 1])
                if token.map[1] <= token.map[0] + 1 or not re.fullmatch(r"\s*" + re.escape(token.markup[0]) + "{" + str(len(token.markup)) + r",}\s*", last):
                    issues.append({"code": "unclosed_fence", "line": token.map[0] + 1})
        html = []
        if token.type == "html_block":
            html.append(token.content)
        for child in token.children or []:
            if child.type in {"link_open", "image"}:
                links.append(child.attrGet("href" if child.type == "link_open" else "src"))
            if child.type == "html_inline":
                html.append(child.content)
        for fragment in html:
            parser = HTML()
            parser.feed(fragment)
            links.extend(parser.links)
            anchors.update(parser.anchors)
            for tag in parser.custom:
                issues.append({"code": "unrendered_component_or_literal", "tag": tag})
    return {"headings": headings, "links": links, "anchors": sorted(anchors), "code": code, "units": units, "issues": issues}


def protected(path, data):
    if path.endswith(".md"):
        return inspect(data.decode("utf-8"))["code"]
    if path.endswith((".py", ".js", ".ts", ".rs", ".c", ".cpp", ".h", ".sh", ".ps1")):
        return [(path.rsplit(".", 1)[-1], data.decode("utf-8"))]
    return []
