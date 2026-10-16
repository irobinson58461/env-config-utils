import unittest

from env_config_utils import Config, ConfigError, get_config


class GetConfigDefaultsTests(unittest.TestCase):
    def test_missing_required_raises(self):
        with self.assertRaises(ConfigError):
            get_config({"port": {"type": "int"}}, environ={})

    def test_missing_optional_uses_default(self):
        cfg = get_config({"debug": {"type": "bool", "default": False}}, environ={})
        self.assertFalse(cfg.debug)

    def test_default_none_when_no_default_and_not_required(self):
        cfg = get_config({"name": {"type": "str", "required": False}}, environ={})
        self.assertIsNone(cfg.name)


class GetConfigEnvNameTests(unittest.TestCase):
    def test_default_env_name_is_uppercased_key(self):
        cfg = get_config({"name": {"type": "str"}}, environ={"NAME": "alice"})
        self.assertEqual(cfg.name, "alice")

    def test_explicit_env_name(self):
        cfg = get_config(
            {"name": {"type": "str", "env": "APP_NAME"}},
            environ={"APP_NAME": "bob"},
        )
        self.assertEqual(cfg.name, "bob")


class GetConfigTypeTests(unittest.TestCase):
    def test_str_passthrough(self):
        cfg = get_config({"name": {}}, environ={"NAME": "hello"})
        self.assertEqual(cfg.name, "hello")

    def test_int_coercion(self):
        cfg = get_config({"port": {"type": "int"}}, environ={"PORT": "8080"})
        self.assertEqual(cfg.port, 8080)
        self.assertIsInstance(cfg.port, int)

    def test_int_invalid_raises_config_error(self):
        with self.assertRaises(ConfigError):
            get_config({"port": {"type": "int"}}, environ={"PORT": "not-a-number"})

    def test_float_coercion(self):
        cfg = get_config({"ratio": {"type": "float"}}, environ={"RATIO": "0.5"})
        self.assertEqual(cfg.ratio, 0.5)
        self.assertIsInstance(cfg.ratio, float)

    def test_float_invalid_raises_config_error(self):
        with self.assertRaises(ConfigError):
            get_config({"ratio": {"type": "float"}}, environ={"RATIO": "nan-text"})

    def test_type_can_be_type_object(self):
        cfg = get_config({"port": {"type": int}}, environ={"PORT": "9090"})
        self.assertEqual(cfg.port, 9090)


class GetConfigBoolTests(unittest.TestCase):
    def test_truthy_values(self):
        for val in ("1", "true", "TRUE", "yes", "Y", "on"):
            with self.subTest(val=val):
                cfg = get_config({"d": {"type": "bool"}}, environ={"D": val})
                self.assertTrue(cfg.d)

    def test_falsy_values(self):
        for val in ("0", "false", "NO", "n", "off", ""):
            with self.subTest(val=val):
                cfg = get_config({"d": {"type": "bool"}}, environ={"D": val})
                self.assertFalse(cfg.d)

    def test_unrecognised_bool_raises_config_error(self):
        with self.assertRaises(ConfigError):
            get_config({"d": {"type": "bool"}}, environ={"D": "maybe"})


class GetConfigRequiredDefaultConflictTests(unittest.TestCase):
    def test_required_and_default_mutually_exclusive(self):
        with self.assertRaises(TypeError):
            get_config({"p": {"type": "int", "required": True, "default": 5}}, environ={})


class ConfigObjectTests(unittest.TestCase):
    def test_repr_round_trips_values(self):
        cfg = get_config({"name": {"type": "str"}}, environ={"NAME": "x"})
        self.assertIn("x", repr(cfg))

    def test_immutable_setattr_raises(self):
        cfg = get_config({"name": {"type": "str"}}, environ={"NAME": "x"})
        with self.assertRaises(AttributeError):
            cfg.name = "y"

    def test_unknown_attribute_raises(self):
        cfg = get_config({"name": {"type": "str"}}, environ={"NAME": "x"})
        with self.assertRaises(AttributeError):
            _ = cfg.nope

    def test_as_dict_returns_copy(self):
        cfg = get_config({"name": {"type": "str"}}, environ={"NAME": "x"})
        d = cfg.as_dict()
        self.assertEqual(d, {"name": "x"})
        d["name"] = "mutated"
        self.assertEqual(cfg.name, "x")

    def test_isinstance_config(self):
        cfg = get_config({"name": {"type": "str"}}, environ={"NAME": "x"})
        self.assertIsInstance(cfg, Config)


class GetConfigIntegrationTests(unittest.TestCase):
    def test_multiple_keys_mixed(self):
        cfg = get_config(
            {
                "name": {"type": "str", "required": False, "default": "anon"},
                "port": {"type": "int", "required": True},
                "debug": {"type": "bool", "default": False},
                "ratio": {"type": "float", "required": False},
            },
            environ={"PORT": "8000", "DEBUG": "true", "RATIO": "1.5"},
        )
        self.assertEqual(cfg.name, "anon")
        self.assertEqual(cfg.port, 8000)
        self.assertTrue(cfg.debug)
        self.assertEqual(cfg.ratio, 1.5)

    def test_empty_spec_returns_empty_config(self):
        cfg = get_config({}, environ={})
        self.assertEqual(cfg.as_dict(), {})


if __name__ == "__main__":
    unittest.main()
