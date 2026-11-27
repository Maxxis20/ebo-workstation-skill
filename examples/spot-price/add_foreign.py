#!/usr/bin/env python3
"""add_foreign.py <bound.xml> - give the values in folder Spot their Foreign address (spot.<name>) again.

deploy.sh binds by a Special export of the example folder, and that export does not carry Foreign addresses
(findings, "MQTT subscription"): without this the values would come back without them and the Prices client,
which finds its targets by Foreign address, would write nothing."""
import re, sys

# Text, not an XML library: the import is particular about the file's form, so only the 120 lines are added.
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
m = re.search(r'<OI NAME="Spot" TYPE="[^"]*"[^>]*>', text)
if not m:
    sys.exit("add_foreign: no folder Spot found")
depth, end = 1, None
for t in re.finditer(r'<OI\b[^>]*?(/?)>|</OI>', text[m.end():]):
    if t.group(0) == "</OI>":
        depth -= 1
        if depth == 0:
            end = m.end() + t.start()
            break
    elif t.group(1) != "/":
        depth += 1
body = text[m.end():end]
body, n = re.subn(r'(<OI NAME="([^"]+)" TYPE="server\.point\.[A-Z]+"[^>]*>.*?)(\s*</OI>)',
                  lambda v: f'{v.group(1)}\n      <PI Name="ForeignAddress" Value="spot.{v.group(2)}"/>{v.group(3)}',
                  body, flags=re.S)
if not n:
    sys.exit("add_foreign: no values in folder Spot")
open(path, "w", encoding="utf-8").write(text[:m.end()] + body + text[end:])
print(f"add_foreign: {n} values in Spot got their Foreign address")
