#!/usr/bin/env python3
"""Включает или отключает автозагрузку Jarvis."""

import sys
from jarvis.autostart import enable, disable, is_enabled


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("off", "disable", "0"):
        print(disable())
    else:
        print(enable())
    print(f"Статус: {'включена' if is_enabled() else 'отключена'}")
