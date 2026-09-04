"""
Plugin discovery for targets and middleware. Both are found two ways:

  1. Built-in: every submodule of the package is imported and scanned for the
     relevant base-class subclass. Drop a file in the folder -> it's registered.
  2. External plugins: entry points (`hyperject.modules` / `hyperject.middleware`),
     so a separate pip/pipx package can ship additional targets or middleware.
"""
from __future__ import annotations

import importlib
import pkgutil

from .base import TargetModule
from .mwbase import Middleware
from . import modules as modules_pkg
from . import middleware as middleware_pkg

_MODULE_CACHE: dict | None = None
_MW_CACHE: dict | None = None


def _scan_pkg(pkg, base_cls, found: dict) -> None:
    for mod_info in pkgutil.iter_modules(pkg.__path__):
        module = importlib.import_module(f"{pkg.__name__}.{mod_info.name}")
        for obj in vars(module).values():
            if (isinstance(obj, type) and issubclass(obj, base_cls)
                    and obj is not base_cls):
                if getattr(obj, "name", ""):
                    found[obj.name] = obj


def _scan_entry_points(group: str, base_cls, found: dict) -> None:
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group=group)
    except Exception:
        return
    for ep in eps:
        try:
            obj = ep.load()
            if isinstance(obj, type) and issubclass(obj, base_cls) and getattr(obj, "name", ""):
                found[obj.name] = obj
        except Exception:
            continue


def discover(force: bool = False) -> dict:
    """Return {name: TargetModule instance}, cached after first call."""
    global _MODULE_CACHE
    if _MODULE_CACHE is not None and not force:
        return _MODULE_CACHE
    classes: dict = {}
    _scan_pkg(modules_pkg, TargetModule, classes)
    _scan_entry_points("hyperject.modules", TargetModule, classes)
    _MODULE_CACHE = {name: cls() for name, cls in sorted(classes.items())}
    return _MODULE_CACHE


def discover_middleware(force: bool = False) -> dict:
    """Return {name: Middleware class} (classes, since they take per-config options)."""
    global _MW_CACHE
    if _MW_CACHE is not None and not force:
        return _MW_CACHE
    classes: dict = {}
    _scan_pkg(middleware_pkg, Middleware, classes)
    _scan_entry_points("hyperject.middleware", Middleware, classes)
    _MW_CACHE = dict(sorted(classes.items()))
    return _MW_CACHE
