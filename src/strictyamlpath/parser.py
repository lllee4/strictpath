"""A small, strict subset of YAML for reading config files.

This is not a general-purpose YAML parser. It handles block mappings,
block sequences, and scalars -- the shapes almost every config file
actually uses. Flow style ({}/[]), anchors/aliases, and multi-line
block scalars (| and >) are not supported yet.

The point of writing this instead of depending on PyYAML is the
strictness policy: things PyYAML quietly resolves one way (the Norway
problem, duplicate keys) are treated as parse errors here unless the
caller opts into --lenient.
"""

import re


class YamlError(Exception):
    def __init__(self, message, line=None):
        self.line = line
        if line is not None:
            message = "line {}: {}".format(line, message)
        super().__init__(message)


class _Line:
    __slots__ = ("no", "indent", "text")

    def __init__(self, no, indent, text):
        self.no = no
        self.indent = indent
        self.text = text


_BOOL_TRUE = {"true", "True", "TRUE"}
_BOOL_FALSE = {"false", "False", "FALSE"}
_NULL = {"null", "Null", "NULL", "~"}
# YAML 1.1 treats these as booleans too, but that surprises people who
# just wanted the string "no" for a hostname or a version tag.
_AMBIGUOUS_BOOL = {
    "yes", "Yes", "YES", "no", "No", "NO",
    "on", "On", "ON", "off", "Off", "OFF",
    "y", "Y", "n", "N",
}
_LEADING_ZERO_RE = re.compile(r"^[+-]?0[0-9]+$")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}


def _strip_comment(raw):
    in_single = False
    in_double = False
    for i, ch in enumerate(raw):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or raw[i - 1] in " \t":
                return raw[:i]
    return raw


def _split_lines(text):
    lines = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped == "" or stripped in ("---", "..."):
            continue
        content = _strip_comment(raw).rstrip()
        if content.strip() == "":
            continue
        indent_str = content[: len(content) - len(content.lstrip(" \t"))]
        if "\t" in indent_str:
            raise YamlError(
                "tab used for indentation; YAML indentation must be spaces",
                lineno,
            )
        indent = len(indent_str)
        lines.append(_Line(lineno, indent, content[indent:]))
    return lines


def _parse_double_quoted(token, lineno):
    inner = token[1:-1]
    out = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner):
            nxt = inner[i + 1]
            if nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
                i += 2
                continue
            raise YamlError("unsupported escape sequence '\\{}'".format(nxt), lineno)
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_scalar(token, lineno, lenient):
    token = token.strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return _parse_double_quoted(token, lineno)
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1].replace("''", "'")
    if token == "" or token in _NULL:
        return None
    if token in _BOOL_TRUE:
        return True
    if token in _BOOL_FALSE:
        return False
    if token in _AMBIGUOUS_BOOL:
        if lenient:
            return token.lower() in ("yes", "on", "y")
        raise YamlError(
            "ambiguous scalar {!r} could be a boolean or a string "
            "(quote it, or rerun with --lenient)".format(token),
            lineno,
        )
    if _LEADING_ZERO_RE.match(token):
        if lenient:
            return token
        raise YamlError(
            "{!r} has a leading zero; ambiguous as a number or a string "
            "(quote it, or rerun with --lenient)".format(token),
            lineno,
        )
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


class _Parser:
    def __init__(self, lines, lenient):
        self.lines = lines
        self.pos = 0
        self.lenient = lenient

    def peek(self):
        return self.lines[self.pos] if self.pos < len(self.lines) else None

    def parse_node(self, indent):
        line = self.peek()
        if line is None or line.indent < indent:
            return None
        if line.text.startswith("- ") or line.text == "-":
            return self.parse_sequence(line.indent)
        return self.parse_mapping(line.indent)

    def parse_sequence(self, indent):
        items = []
        while True:
            line = self.peek()
            if line is None or line.indent != indent:
                break
            if not (line.text.startswith("- ") or line.text == "-"):
                break
            self.pos += 1
            if line.text == "-":
                rest, rest_col = "", line.indent + 1
            else:
                after_dash = line.text[1:]
                stripped = after_dash.lstrip(" ")
                spaces = len(after_dash) - len(stripped)
                rest, rest_col = stripped, line.indent + 1 + spaces

            if rest == "":
                nxt = self.peek()
                value = self.parse_node(nxt.indent) if nxt and nxt.indent > indent else None
            elif rest.startswith("- ") or rest == "-":
                raise YamlError(
                    "nested compact sequences ('- - item') are not supported yet",
                    line.no,
                )
            elif self._looks_like_mapping_entry(rest):
                value = self._parse_mapping_body(rest_col, rest, line.no)
            else:
                value = _parse_scalar(rest, line.no, self.lenient)
            items.append(value)
        return items

    def parse_mapping(self, indent):
        line = self.peek()
        self.pos += 1
        return self._parse_mapping_body(indent, line.text, line.no)

    def _looks_like_mapping_entry(self, rest):
        key, sep, _ = rest.partition(":")
        if not sep:
            return False
        after = rest[len(key) + 1:]
        return after == "" or after.startswith(" ")

    def _parse_mapping_body(self, indent, first_text, first_lineno):
        result = {}
        seen = {}
        self._consume_mapping_entry(result, seen, indent, first_text, first_lineno)
        while True:
            line = self.peek()
            if line is None or line.indent != indent:
                break
            if line.text.startswith("- ") or line.text == "-":
                break
            self.pos += 1
            self._consume_mapping_entry(result, seen, indent, line.text, line.no)
        return result

    def _consume_mapping_entry(self, result, seen, indent, text, lineno):
        key_raw, sep, value_raw = text.partition(":")
        after = text[len(key_raw) + 1:]
        if not sep or (after and not after.startswith(" ")):
            raise YamlError("expected 'key: value' but found {!r}".format(text), lineno)

        key = _parse_scalar(key_raw.strip(), lineno, self.lenient)
        if not isinstance(key, str):
            # path queries are always strings, so keys are kept as the
            # text the user wrote rather than as the coerced type.
            key = key_raw.strip()

        if key in seen and not self.lenient:
            raise YamlError(
                "duplicate key {!r} (first seen on line {}); "
                "rerun with --lenient to let the last one win".format(key, seen[key]),
                lineno,
            )
        seen[key] = lineno

        value_raw = value_raw.strip()
        if value_raw == "":
            nxt = self.peek()
            value = self.parse_node(nxt.indent) if nxt and nxt.indent > indent else None
        else:
            value = _parse_scalar(value_raw, lineno, self.lenient)
        result[key] = value


def load(text, lenient=False):
    lines = _split_lines(text)
    if not lines:
        return None
    parser = _Parser(lines, lenient)
    value = parser.parse_node(lines[0].indent)
    if parser.pos != len(parser.lines):
        raise YamlError("unexpected indentation change", parser.lines[parser.pos].no)
    return value
