# strictpath

Answers one question: what's the value at this path in this YAML file?

`yq` and `jq` both do this, but they build on parsers that quietly
resolve YAML's ambiguous corners for you -- a bare `no` becomes the
boolean `false`, a repeated key silently takes its last value, and you
never find out unless you already knew to look. That's fine for a
one-off query, but not for CI checks or scripts that trust the output.
strictpath's default mode fails loudly on that kind of ambiguity
instead of guessing, and gives you `--lenient` for when you just want
an answer despite the mess.

It has no dependencies. The YAML support is a small hand-written
parser (see `src/strictyamlpath/parser.py`) that covers block mappings,
block sequences, and scalars -- the shapes almost every config file
actually uses. It does not (yet) support flow style (`{}`/`[]`),
anchors/aliases, or multi-line block scalars (`|`, `>`).

## Usage

Given `config.yaml`:

```yaml
server:
  host: db01
  port: 5432
  tls: true
  tags:
    - primary
    - us-east
```

```
$ strictpath config.yaml server.port
5432

$ strictpath config.yaml server.tags[0]
primary

$ strictpath config.yaml server.missing
strictpath: key 'missing' not found at 'server'
$ echo $?
1

$ strictpath config.yaml server.tags --default none
none
```

## Strict by default

Two common YAML footguns are treated as errors unless you pass
`--lenient`:

Duplicate keys:

```yaml
flags:
  debug: false
  debug: true
```

```
$ strictpath config.yaml flags.debug
strictpath: line 3: duplicate key 'debug' (first seen on line 2); rerun with --lenient to let the last one win
$ strictpath --lenient config.yaml flags.debug
true
```

Ambiguous bare scalars (the "Norway problem" -- `no`, `yes`, `on`,
`off`, `y`, `n` are booleans under YAML 1.1 but look like ordinary
strings to a human):

```yaml
region:
  name: no
```

```
$ strictpath config.yaml region.name
strictpath: line 2: ambiguous scalar 'no' could be a boolean or a string (quote it, or rerun with --lenient)
$ strictpath --lenient config.yaml region.name
false
```

The fix that doesn't need `--lenient` at all: quote the value in the
source file (`name: "no"`).

## Path syntax

Dotted keys, with `[N]` for sequence indices: `a.b.c`, `hosts[0].name`,
`items[2]`. Exit code is 0 on success, 1 if the path doesn't resolve
(unless `-d/--default` is given), 2 for a bad file or a strict parse
failure, 3 if the path resolves to a mapping or sequence rather than a
scalar.

## Install

No PyPI package yet. Run it from a checkout:

```
$ pip install -e .
$ strictpath config.yaml server.port
```

or without installing:

```
$ python -m strictyamlpath.cli config.yaml server.port
```

Requires Python 3.9+. Standard library only.
