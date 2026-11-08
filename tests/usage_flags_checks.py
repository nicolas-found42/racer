#!/usr/bin/env python3
"""Every command-line flag the parser accepts must be documented in the usage text."""
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
parsed = sorted(set(re.findall(r'a\s*==\s*"(--[a-z0-9-]+)"', source)))
start = source.index("Usage: racer")
end = source.index("return 1", start)
usage = source[start:end]
missing = [flag for flag in parsed if flag not in usage]
if not parsed:
    raise SystemExit("no flags parsed: the check pattern no longer matches main.cpp")
if missing:
    raise SystemExit("flags accepted but missing from usage: " + ", ".join(missing))
print(f"usage text documents all {len(parsed)} accepted flags PASS")
