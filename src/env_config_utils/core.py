from __future__ import annotations

import os
from typing import Any, Callable, Mapping

__all__ = ["Config", "ConfigError", "get_config"]


class ConfigError(ValueError):
    """Raised when a required environment variable is missing or cannot be coerced."""


class Config:
    """Simple attribute container for resolved configuration values.

    Using a plain class with ``__slots__`` keeps attribute access fast and typo-proof
    (``cfg.pasword`` raises ``AttributeError`` instead of silently returning ``None``).
    """

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_values", dict(values))

    def __getattr__(self, name: str) -> Any:
        # ``__getattr__`` is only called when normal attribute lookup fails, so
        # this never shadows real attributes or dunder names that exist.
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Config is immutable; set values in the spec, not on the object")

    def __repr__(self) -> str:
        return f"Config({self._values!r})"

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of all resolved values as a plain dict."""
        return dict(self._values)


def _coerce_bool(value: str) -> bool:
    """Coerce a handful of human-friendly truthy/falsy strings to ``bool``.

    Why not just ``bool(value)``? Because every non-empty string (including ``"false"``)
    would be truthy under that rule, which is never what a config consumer wants.
    """
    lowered = value.strip().lower()
    if lowered in ("1", "true", "yes", "y", "on"):
        return True
    if lowered in ("0", "false", "no", "n", "off", ""):
        return False
    raise ConfigError(f"cannot coerce {value!r} to bool")


# Each coercer is a plain function (str -> T) so the dispatch table is trivial and
# users can pass their own callables without subclassing anything.
_COERCERS: dict[str, Callable[[str], Any]] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": _coerce_bool,
}


def _build_spec(spec: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate and normalise a spec into ``{key: {env, type, default, required}}``."""
    normalised: dict[str, dict[str, Any]] = {}
    for key, raw in spec.items():
        if not isinstance(raw, Mapping):
            raise TypeError(f"spec for {key!r} must be a mapping, got {type(raw).__name__}")

        env = raw.get("env", key.upper())
        if not isinstance(env, str) or not env:
            raise TypeError(f"spec for {key!r}: 'env' must be a non-empty string")

        type_name = raw.get("type", "str")
        if isinstance(type_name, type):
            # Accept ``str`` / ``int`` etc. as type objects for ergonomics, but
            # resolve to the string key so custom callables and built-ins share
            # one dispatch path.
            type_name = type_name.__name__
        if type_name not in _COERCERS:
            raise TypeError(
                f"spec for {key!r}: unsupported type {type_name!r} "
                f"(expected one of {sorted(_COERCERS)})"
            )

        default = raw.get("default", None)
        required = bool(raw.get("required", default is None))
        if required and default is not None:
            # A required key with a default is self-contradictory. We pick one
            # interpretation — required wins — and complain loudly rather than
            # silently picking a behaviour.
            raise TypeError(
                f"spec for {key!r}: 'required' and 'default' are mutually exclusive"
            )

        normalised[key] = {
            "env": env,
            "type": type_name,
            "default": default,
            "required": required,
        }
    return normalised


def _resolve_one(key: str, entry: dict[str, Any], environ: Mapping[str, str]) -> Any:
    env_name = entry["env"]
    coercer = _COERCERS[entry["type"]]

    if env_name not in environ:
        if entry["required"]:
            raise ConfigError(f"missing required environment variable: {env_name}")
        return entry["default"]

    raw = environ[env_name]
    try:
        return coercer(raw)
    except ConfigError:
        raise
    except ValueError as exc:
        raise ConfigError(f"cannot coerce {env_name}={raw!r} to {entry['type']}: {exc}") from exc


def get_config(spec: Mapping[str, Any], *, environ: Mapping[str, str] | None = None) -> Config:
    """Build a :class:`Config` from an environment according to ``spec``.

    Parameters
    ----------
    spec:
        Mapping of config-key to a spec dict. Supported fields per key:

        - ``env`` (str, default: ``key.upper()``): the environment variable to read.
        - ``type`` (str or type, default ``"str"``): one of ``str``, ``int``,
          ``float``, ``bool``.
        - ``default``: value used when the env var is absent and the key is
          not required. If omitted, the key is required by default.
        - ``required`` (bool): when ``True``, a missing env var raises
          :class:`ConfigError`. Mutually exclusive with ``default``.

    environ:
        Optional mapping to read instead of ``os.environ``. Pass it in tests so
        the suite is deterministic and never touches the real environment.
    """
    normalised = _build_spec(spec)
    env_source = os.environ if environ is None else environ
    resolved: dict[str, Any] = {}
    for key, entry in normalised.items():
        resolved[key] = _resolve_one(key, entry, env_source)
    return Config(resolved)
