"""Discovering agents, including agents written by other student groups.

A plugin is any .py file dropped into the `plugins/` folder (or given by path). It can provide:

  (a) one or more classes subclassing `tank_battle.agents.BaseAgent`, or
  (b) a plain function  `get_action(observation: dict, player_id: int) -> str`
      (no import of our code needed; `observation` is `GameState.to_dict()`).
      Optional module variable AGENT_NAME gives the display name.

Agents are referred to by a spec string:
  "Heuristic Alpha-Beta"                 a registered name
  "plugins/group7.py"                    every agent in the file (first one is used)
  "plugins/group7.py:MyAgent"            a specific class / function in the file
"""

import importlib.util
import inspect
import os
import sys

from ..core.constants import Action
from .base_agent import BaseAgent

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGINS_DIR = os.path.join(PROJECT_DIR, "plugins")


class FunctionAgent(BaseAgent):
    """Adapter turning a `get_action(observation, player_id)` function into an agent."""

    def __init__(self, player, function, name, **kwargs):
        super().__init__(player)
        self.function = function
        self.name = name

    def choose_action(self, state):
        return Action.parse(self.function(state.to_dict(), self.player))


class AgentEntry:
    """A named factory: entry.create(player_id) -> BaseAgent instance."""

    def __init__(self, name, factory, source="built-in", description=""):
        self.name = name
        self.factory = factory
        self.source = source
        self.description = description

    def create(self, player):
        agent = self.factory(player)
        agent.name = self.name
        return agent

    def __repr__(self):
        return "AgentEntry(%r, %s)" % (self.name, self.source)


def _import_file(path):
    path = os.path.abspath(path)
    module_name = "tank_plugin_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    plugin_dir = os.path.dirname(path)
    if plugin_dir not in sys.path:      # lets a plugin import its own helper modules
        sys.path.insert(0, plugin_dir)
    spec.loader.exec_module(module)
    return module


def entries_from_file(path):
    module = _import_file(path)
    source = os.path.basename(path)
    entries = []
    for attr, obj in vars(module).items():
        if (inspect.isclass(obj) and issubclass(obj, BaseAgent) and not inspect.isabstract(obj)
                and obj.__module__ == module.__name__):
            name = getattr(obj, "name", attr)
            if name in ("Agent", BaseAgent.name):
                name = attr
            entries.append(AgentEntry(name, obj, source, getattr(obj, "description", "")))
    function = getattr(module, "get_action", None)
    if callable(function):
        name = getattr(module, "AGENT_NAME", os.path.splitext(source)[0])
        entries.append(AgentEntry(name, lambda p, f=function, n=name: FunctionAgent(p, f, n), source,
                                  "function plugin"))
    return entries


def discover_plugins(directory=PLUGINS_DIR):
    """Load every plugin in `directory`. A broken plugin is reported, not fatal."""
    entries, errors = [], []
    if not os.path.isdir(directory):
        return entries, errors
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(directory, filename)
            try:
                entries.extend(entries_from_file(path))
            except Exception as exc:   # noqa: BLE001 - foreign code may raise anything
                errors.append("%s: %s" % (filename, exc))
    return entries, errors


def resolve_agent(spec, registry):
    """Turn a spec string into an AgentEntry (see module docstring)."""
    for entry in registry:
        if entry.name.lower() == spec.lower():
            return entry
    path, _, member = spec.partition(":")
    if path.endswith(".py") and os.path.isfile(path):
        entries = entries_from_file(path)
        if member:
            entries = [e for e in entries if e.name == member or getattr(e.factory, "__name__", "") == member]
        if entries:
            return entries[0]
    raise ValueError("Unknown agent %r. Available: %s" % (spec, ", ".join(e.name for e in registry)))
