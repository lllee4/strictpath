import unittest

from strictyamlpath.path import PathError, parse_path, resolve


class ParsePathTests(unittest.TestCase):
    def test_dotted_keys(self):
        self.assertEqual(
            parse_path("a.b.c"),
            [("key", "a"), ("key", "b"), ("key", "c")],
        )

    def test_leading_key_without_dot(self):
        self.assertEqual(parse_path("a"), [("key", "a")])

    def test_index(self):
        self.assertEqual(
            parse_path("hosts[0].name"),
            [("key", "hosts"), ("index", 0), ("key", "name")],
        )

    def test_multiple_indices(self):
        self.assertEqual(
            parse_path("items[2][3]"),
            [("key", "items"), ("index", 2), ("index", 3)],
        )

    def test_unterminated_bracket_raises(self):
        with self.assertRaises(ValueError):
            parse_path("a[0")

    def test_non_numeric_index_raises(self):
        with self.assertRaises(ValueError):
            parse_path("a[x]")

    def test_negative_index_raises(self):
        with self.assertRaises(ValueError):
            parse_path("a[-1]")


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "server": {
                "host": "db01",
                "port": 5432,
                "tags": ["primary", "us-east"],
                "hosts": [{"name": "a"}, {"name": "b"}],
            }
        }

    def test_resolve_nested_key(self):
        self.assertEqual(resolve(self.data, parse_path("server.host")), "db01")

    def test_resolve_index(self):
        self.assertEqual(resolve(self.data, parse_path("server.tags[1]")), "us-east")

    def test_resolve_key_after_index(self):
        self.assertEqual(
            resolve(self.data, parse_path("server.hosts[1].name")), "b"
        )

    def test_resolve_whole_mapping(self):
        self.assertEqual(resolve(self.data, parse_path("server")), self.data["server"])

    def test_missing_key_raises(self):
        with self.assertRaises(PathError):
            resolve(self.data, parse_path("server.missing"))

    def test_key_on_non_mapping_raises(self):
        with self.assertRaises(PathError):
            resolve(self.data, parse_path("server.host.nope"))

    def test_index_on_non_sequence_raises(self):
        with self.assertRaises(PathError):
            resolve(self.data, parse_path("server.host[0]"))

    def test_index_out_of_range_raises(self):
        with self.assertRaises(PathError):
            resolve(self.data, parse_path("server.tags[5]"))


if __name__ == "__main__":
    unittest.main()
