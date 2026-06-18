#!/usr/bin/env python3
"""Synthetic local-only CTF fixture for skill forward testing."""

from __future__ import annotations


FLAG = "flag{friendly_login_state_machine}"


def login(username: str, password: str) -> str:
    if username == "admin" and password == "correct-horse-battery-staple":
        return FLAG
    return "nope"


if __name__ == "__main__":
    print("Friendly Login fixture. Inspect source; no server is started.")
