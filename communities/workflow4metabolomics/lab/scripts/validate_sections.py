#!/usr/bin/env python3
"""Validate numbered lab sections against the Galaxy Labs schema."""

import glob

import yaml
from labs_engine.labs.lab_schema import LabSectionSchema

total = 0
for f in sorted(glob.glob("sections/[0-9]*.yml")):
    data = yaml.safe_load(open(f))
    s = LabSectionSchema.model_validate(data)
    tab = next((t for t in s.tabs if t.id == "tools"), None)
    if tab and isinstance(tab.content, dict) and "subsections" in tab.content:
        subs = [(x.id, len(x.content)) for x in tab.content["subsections"]]
        n = sum(c for _, c in subs)
        total += n
        print(f"{f}: OK ({n} tool entries) {subs}")
    else:
        print(f"{f}: OK (no tools subsections)")
print("total tool entries across sections:", total)
