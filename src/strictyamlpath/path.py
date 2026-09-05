"""Dotted-path parsing and resolution against loaded YAML data."""


class PathError(Exception):
    pass


def parse_path(path_str):
    ops = []
    i = 0
    n = len(path_str)
    while i < n:
        ch = path_str[i]
        if ch == ".":
            i += 1
            continue
        if ch == "[":
            end = path_str.find("]", i)
            if end == -1:
                raise ValueError("unterminated '[' in path at position {}".format(i))
            idx_str = path_str[i + 1:end]
            if not idx_str.isdigit():
                raise ValueError("expected a numeric index inside [], got {!r}".format(idx_str))
            ops.append(("index", int(idx_str)))
            i = end + 1
            continue
        j = i
        while j < n and path_str[j] not in ".[":
            j += 1
        ops.append(("key", path_str[i:j]))
        i = j
    return ops


def _format_trail(trail):
    out = ""
    for kind, val in trail:
        if kind == "key":
            out += "." + val if out else val
        else:
            out += "[{}]".format(val)
    return out or "$"


def resolve(data, ops):
    node = data
    trail = []
    for kind, val in ops:
        if kind == "key":
            if not isinstance(node, dict):
                raise PathError(
                    "cannot use key {!r} on a non-mapping at {!r}".format(val, _format_trail(trail))
                )
            if val not in node:
                raise PathError(
                    "key {!r} not found at {!r}".format(val, _format_trail(trail))
                )
            node = node[val]
        else:
            if not isinstance(node, list):
                raise PathError(
                    "cannot index [{}] on a non-sequence at {!r}".format(val, _format_trail(trail))
                )
            if val < 0 or val >= len(node):
                raise PathError(
                    "index [{}] out of range at {!r}".format(val, _format_trail(trail))
                )
            node = node[val]
        trail.append((kind, val))
    return node
