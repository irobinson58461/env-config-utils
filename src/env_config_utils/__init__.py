"""env-config-utils: load configuration from the environment with type coercion.

Public API
----------
- ``get_config(spec)``: return a ``Config`` object with typed attributes.
- ``Config``: the result type returned by ``get_config``; mostly an implementation
  detail but exported for ``isinstance`` checks and type hints.
- ``ConfigError``: raised when the environment does not satisfy the spec.
"""

from .core import Config, ConfigError, get_config

__all__ = ["Config", "ConfigError", "get_config"]
