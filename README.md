# env-config-utils

Load configuration from the environment with type coercion. No third-party packages.

```python
from env_config_utils import get_config, Config, ConfigError

cfg = get_config({
    "name": {"type": "str", "default": "anon"},
    "port": {"type": "int", "required": True},
    "debug": {"type": "bool", "default": False},
    "ratio": {"type": "float", "required": False},
}, environ={"PORT": "8000", "DEBUG": "true", "RATIO": "1.5"})

print(cfg.name, cfg.port, cfg.debug, cfg.ratio)
# anon 8000 True 1.5
```

## Why

Reading environment variables directly means every consumer repeats the same
`int(os.environ["X"])` boilerplate and the same missing-variable checks. This
library collapses that to one declarative spec and gives back an immutable
object with typed attributes, so typos like `cfg.pasword` fail immediately
instead of silently returning `None`.

The trade-off: instead of pydantic-style schemas with validation, inheritance,
and nested models, this is a flat `key -> {type, env, default, required}`
mapping. It covers the common case and stops there.

## Awkward edges

- **Booleans.** `bool("false")` is `True` in Python because every non-empty
  string is truthy. This library accepts a fixed set of strings
  (`1`/`true`/`yes`/`y`/`on` as true; `0`/`false`/`no`/`n`/`off`/`""` as false)
  and raises `ConfigError` for anything else. If you need `"1"`/`"0"`-only
  semantics, pass a custom coercer — but the built-in set is intentionally
  small and fixed.

- **`required` vs `default`.** These are mutually exclusive. A key is required
  by default (no `default` given); set `"default": None` explicitly if you
  want an optional key whose value is `None`.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
