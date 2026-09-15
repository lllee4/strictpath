import unittest

from strictyamlpath.parser import YamlError, load


class LoadMappingsTests(unittest.TestCase):
    def test_flat_mapping(self):
        data = load("a: 1\nb: 2\n")
        self.assertEqual(data, {"a": 1, "b": 2})

    def test_nested_mapping(self):
        text = (
            "server:\n"
            "  host: db01\n"
            "  port: 5432\n"
            "  tags:\n"
            "    - primary\n"
            "    - us-east\n"
        )
        data = load(text)
        self.assertEqual(
            data,
            {
                "server": {
                    "host": "db01",
                    "port": 5432,
                    "tags": ["primary", "us-east"],
                }
            },
        )

    def test_sequence_of_mappings(self):
        text = "- name: a\n  value: 1\n- name: b\n  value: 2\n"
        data = load(text)
        self.assertEqual(
            data,
            [{"name": "a", "value": 1}, {"name": "b", "value": 2}],
        )

    def test_sequence_of_plain_strings(self):
        data = load("- alpha\n- beta\n")
        self.assertEqual(data, ["alpha", "beta"])

    def test_empty_value_is_null(self):
        data = load("a:\n")
        self.assertIsNone(data["a"])

    def test_explicit_null_forms(self):
        self.assertIsNone(load("a: null\n")["a"])
        self.assertIsNone(load("a: ~\n")["a"])

    def test_comment_is_stripped(self):
        data = load("a: 1 # trailing comment\nb: 2\n")
        self.assertEqual(data, {"a": 1, "b": 2})

    def test_hash_inside_quotes_is_not_a_comment(self):
        data = load('a: "not # a comment"\n')
        self.assertEqual(data, {"a": "not # a comment"})


class ScalarTests(unittest.TestCase):
    def test_integers_and_floats(self):
        data = load("i: 42\nf: 3.14\nneg: -7\n")
        self.assertEqual(data, {"i": 42, "f": 3.14, "neg": -7})

    def test_plain_booleans(self):
        data = load("a: true\nb: false\n")
        self.assertEqual(data, {"a": True, "b": False})

    def test_double_quoted_escapes(self):
        data = load('msg: "line1\\nline2"\n')
        self.assertEqual(data["msg"], "line1\nline2")

    def test_single_quoted_doubled_quote_escape(self):
        data = load("s: 'it''s ok'\n")
        self.assertEqual(data["s"], "it's ok")

    def test_unsupported_double_quote_escape_raises(self):
        with self.assertRaises(YamlError):
            load('a: "bad \\q escape"\n')


class StrictnessTests(unittest.TestCase):
    def test_duplicate_key_raises_by_default(self):
        with self.assertRaises(YamlError):
            load("a: 1\na: 2\n")

    def test_duplicate_key_lenient_keeps_last(self):
        data = load("a: 1\na: 2\n", lenient=True)
        self.assertEqual(data, {"a": 2})

    def test_ambiguous_bool_raises_by_default(self):
        with self.assertRaises(YamlError):
            load("region: no\n")

    def test_ambiguous_bool_lenient_resolves(self):
        self.assertIs(load("region: no\n", lenient=True)["region"], False)
        self.assertIs(load("region: yes\n", lenient=True)["region"], True)

    def test_leading_zero_raises_by_default(self):
        with self.assertRaises(YamlError):
            load("port: 007\n")

    def test_leading_zero_lenient_keeps_string(self):
        data = load("port: 007\n", lenient=True)
        self.assertEqual(data["port"], "007")


class StructuralErrorTests(unittest.TestCase):
    def test_tab_indentation_raises(self):
        with self.assertRaises(YamlError):
            load("a:\n\tb: 1\n")

    def test_nested_compact_sequence_raises(self):
        with self.assertRaises(YamlError):
            load("- - a\n")

    def test_malformed_entry_raises(self):
        with self.assertRaises(YamlError):
            load("not a mapping entry\n")


if __name__ == "__main__":
    unittest.main()
