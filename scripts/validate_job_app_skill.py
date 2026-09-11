"""Lightweight skill folder checks (no external deps)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "job-app-filler"
errors: list[str] = []
warnings: list[str] = []


def err(m: str) -> None:
    errors.append(m)


def warn(m: str) -> None:
    warnings.append(m)


def main() -> int:
    if not ROOT.is_dir():
        print(f"FAIL missing skill dir: {ROOT}")
        return 1
    skill = ROOT / "SKILL.md"
    if not skill.is_file():
        err("missing SKILL.md")
    else:
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---"):
            err("SKILL.md missing frontmatter")
        else:
            fm = text.split("---", 2)[1]
            name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
            desc_m = re.search(r"^description:\s*(.+)$", fm, re.M)
            if not name_m or name_m.group(1).strip() != "job-app-filler":
                err("frontmatter name must be job-app-filler")
            if not desc_m or len(desc_m.group(1).strip()) < 40:
                err("description too short")
            desc = desc_m.group(1) if desc_m else ""
            for phrase in ("网申", "北森", "提交"):
                if phrase not in desc:
                    warn(f"description missing trigger-like phrase: {phrase}")
        for needle in ("验证码", "Never", "永不", "提交", "references/form-mapping"):
            if needle not in text and needle != "Never":
                # Chinese body
                pass
        for required in ("永不", "提交", "references/form-mapping.md", "references/safety-checklist.md"):
            if required not in text:
                err(f"SKILL.md missing required content: {required}")
        if len(text) > 20000:
            warn("SKILL.md quite large; consider moving detail to references")

    for rel in (
        "locales/zh-CN.json",
        "locales/en-US.json",
        "references/form-mapping.md",
        "references/profile-schema.md",
        "references/safety-checklist.md",
        "assets/profile.example.yaml",
    ):
        p = ROOT / rel
        if not p.is_file():
            err(f"missing {rel}")

    for loc in ("locales/zh-CN.json", "locales/en-US.json"):
        p = ROOT / loc
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                err(f"{loc} invalid JSON: {e}")
                continue
            if set(data.keys()) != {"displayName", "brief"}:
                err(f"{loc} keys must be exactly displayName,brief — got {list(data)}")

    example = ROOT / "assets" / "profile.example.yaml"
    if example.is_file():
        y = example.read_text(encoding="utf-8")
        if "52020220050213081X" in y:
            err("example profile contains a real-looking personal id from resume")
        if not re.search(r"awards:", y):
            err("example profile missing awards")

    # ensure no README inside skill folder
    if (ROOT / "README.md").exists():
        err("README.md must not live inside the skill folder")

    if errors:
        print("FAIL")
        for e in errors:
            print("  ERROR:", e)
        for w in warnings:
            print("  WARN:", w)
        return 1
    print("PASS")
    for w in warnings:
        print("  WARN:", w)
    print(f"skill dir: {ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
