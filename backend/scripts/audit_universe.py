import re

file2 = r"F:\job wala project\govt\india_government_job_source_universe_12000_targets.md"

with open(file2, "r", encoding="utf-8") as f:
    text = f.read()

for line in text.splitlines():
    line_s = line.strip()
    if line_s.startswith("### ") or line_s.startswith("## "):
        print(line_s)
