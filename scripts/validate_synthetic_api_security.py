#!/usr/bin/env python3
"""Compatibility wrapper for goal004 security validation."""

from __future__ import annotations

import sys

from scripts.validate_goal004_security_controls import main, validate


if __name__ == "__main__":
    sys.exit(main())
