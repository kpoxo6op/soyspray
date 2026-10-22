#!/usr/bin/env python3
"""Drive Android TV settings screens over ADB for options without a settings key.

Usage:
  tv_ui.py SERIAL open ACTION                  start a screen by intent action
  tv_ui.py SERIAL select LABEL [LABEL ...]     focus each row in turn and press OK
  tv_ui.py SERIAL switch LABEL on|off          set the toggle in LABEL's row
  tv_ui.py SERIAL switch '*' on|off            set the screen's only toggle
  tv_ui.py SERIAL texts                        print the visible texts

The screen is read with uiautomator and focus moves with the D-pad, as the
remote would. A confirmation dialog after a toggle is accepted with OK.
`switch` prints `changed` or `ok`, so Ansible can report changes.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

UP, DOWN, LEFT, RIGHT, OK = "19", "20", "21", "22", "23"
MAX_MOVES = 25
NEW_CLEAR_TASK = "0x10008000"  # FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_CLEAR_TASK


class Screen:
    def __init__(self, serial: str):
        self.serial = serial

    def adb(self, *args: str) -> str:
        result = subprocess.run(
            ["adb", "-s", self.serial, *args], capture_output=True, text=True, timeout=60
        )
        if result.returncode:
            raise RuntimeError(f"adb {' '.join(args)}: {result.stderr.strip()}")
        return result.stdout

    def key(self, code: str) -> None:
        self.adb("shell", "input", "keyevent", code)
        time.sleep(0.8)

    def nodes(self) -> list[dict]:
        xml = self.adb(
            "shell", "uiautomator dump /sdcard/tv-ui.xml >/dev/null && cat /sdcard/tv-ui.xml"
        )
        root = ET.fromstring(xml[xml.index("<?xml") :])
        found = []
        for node in root.iter("node"):
            x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds", "[0,0][0,0]")))
            found.append(
                {
                    "text": node.get("text", ""),
                    "focused": node.get("focused") == "true",
                    "checkable": node.get("checkable") == "true",
                    "checked": node.get("checked") == "true",
                    "box": (x1, y1, x2, y2),
                }
            )
        return found

    def texts(self) -> list[str]:
        return [node["text"] for node in self.nodes() if node["text"]]


def inside(inner: tuple, outer: tuple) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def targets(nodes: list[dict], label: str) -> list[dict]:
    if label == "*":
        return [node for node in nodes if node["checkable"]]
    return [node for node in nodes if node["text"] == label]


def step_towards(target: tuple, row: tuple) -> str:
    """Pick the D-pad key that moves focus from ROW towards TARGET."""
    if target[3] <= row[1]:
        return UP
    if target[1] >= row[3]:
        return DOWN
    return LEFT if target[2] <= row[0] else RIGHT


def focus(screen: Screen, label: str) -> tuple[list[dict], dict]:
    """Move the D-pad focus onto the row that shows LABEL (or the toggle for '*')."""
    for _ in range(MAX_MOVES):
        nodes = screen.nodes()
        rows = [node for node in nodes if node["focused"]]
        row = rows[-1] if rows else None
        wanted = targets(nodes, label)
        if row and any(inside(node["box"], row["box"]) for node in wanted):
            return nodes, row
        if row and wanted:
            screen.key(step_towards(wanted[0]["box"], row["box"]))
        else:
            screen.key(DOWN)
    raise RuntimeError(f"could not focus {label!r}; visible: {screen.texts()}")


def toggle_state(screen: Screen, label: str) -> bool:
    nodes, row = focus(screen, label)
    toggles = [node for node in nodes if node["checkable"] and inside(node["box"], row["box"])]
    if not toggles:
        raise RuntimeError(f"{label!r} has no toggle")
    return toggles[0]["checked"]


def switch(screen: Screen, label: str, want: bool) -> str:
    if toggle_state(screen, label) == want:
        return "ok"
    screen.key(OK)
    time.sleep(1)
    texts = screen.texts()
    if "OK" in texts and not any(node["checkable"] for node in screen.nodes()):
        focus(screen, "OK")
        screen.key(OK)
        time.sleep(1)
    if toggle_state(screen, label) != want:
        raise RuntimeError(f"{label!r} did not change")
    return "changed"


def main(argv: list[str]) -> int:
    serial, command, *args = argv
    screen = Screen(serial)
    if command == "open":
        # Clear the task, or a running Settings task resumes on its last screen.
        screen.adb("shell", "am", "start", "-f", NEW_CLEAR_TASK, "-a", args[0])
        time.sleep(3)
    elif command == "select":
        for label in args:
            focus(screen, label)
            screen.key(OK)
            time.sleep(1.5)
    elif command == "switch":
        print(switch(screen, args[0], args[1] == "on"))
    elif command == "texts":
        print("\n".join(screen.texts()))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
