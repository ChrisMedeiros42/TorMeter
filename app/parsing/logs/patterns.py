"""Compiled regex patterns used by combat log parsing."""

from __future__ import annotations

import re

LINE_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\]"
    r"\s+\[([^\]]*)\]"
    r"\s+\[([^\]]*)\]"
    r"\s+\[([^\]]*)\]"
    r"\s+\[([^\]]*)\]"
    r"(?:\s+\(([^)]*)\))?"
    r"(?:\s+<([\d.]+)>)?"
)

PLAYER_RE = re.compile(r"^@([^#/|]+)#(\d+)\|[^|]+\|\((\d+)/(\d+)\)$")
COMPANION_RE = re.compile(r"^@[^/]*/(.+?)\s+\{\d+\}:\d+\|[^|]+\|\((\d+)/(\d+)\)$")
NPC_RE = re.compile(r"^([^@{][^{]*?)\s+\{\d+\}:\d+\|[^|]+\|\((\d+)/(\d+)\)$")

EFFECT_RE = re.compile(r"^(.+?)\s+\{(\d+)\}:\s*(.+?)\s+\{(\d+)\}$")
ABILITY_RE = re.compile(r"^(.*?)\s*\{(\d+)\}$")

VAL_MITIG_TYPE_RE = re.compile(r"^(\d+)(\*)?\s+~(\d+)\s+([-\w]+)(?:\s+\{\d+\})?$")
VAL_MITIG_RE = re.compile(r"^(\d+)(\*)?\s+~(\d+)$")
VAL_TYPE_RE = re.compile(r"^(\d+)(\*)?\s+([-\w]+)(?:\s+\{\d+\})?$")
VAL_NUM_RE = re.compile(r"^(\d+(?:\.\d+)?)$")
