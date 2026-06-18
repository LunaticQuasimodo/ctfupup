#!/usr/bin/env python3
"""Synthetic reverse fixture."""

import codecs


ENCODED = "synt{eri_fgngr_znpuvar}"


def check(candidate: str) -> bool:
    return codecs.encode(candidate, "rot_13") == ENCODED
