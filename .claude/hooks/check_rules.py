"""Enforce the mechanically-checkable bedrock-protocol rules.

Wired from .claude/settings.json as Pre/PostToolUse hooks. Reads the hook JSON
payload on stdin, runs the checks that apply to the event and tool, and exits 2
with an explanation on the first violation -- which blocks the call and feeds the
message back to the model. Any internal failure exits 0, so a bug in this script
never blocks work on its own.

All enforced rules live in .claude/rules/style.md:
  - no non-ASCII characters in edited text
  - no `from __future__ import annotations` in a .py file
  - `ruff check` passes on an edited .py file
  - no `//` prose comments emitted from a Jinja template
  - no `Co-Authored-By` trailer on `git commit`
"""

import json
import re
import subprocess
import sys
from pathlib import Path

EDIT_TOOLS = ("Edit", "Write", "MultiEdit")

# Jinja comment / expression / statement spans. Their `//` never reaches the
# generated C++, so they must be ignored by the template-comment check.
_JINJA = re.compile(r"\{#.*?#\}|\{\{.*?\}\}|\{%.*?%\}", re.S)


def block(rule, message):
    sys.stderr.write(f"[rule:{rule}] {message}\n")
    sys.exit(2)


def candidate_texts(tool_name, tool_input):
    """The new text this edit would introduce, as (label, text) pairs."""
    if tool_name == "Write":
        return [("content", tool_input.get("content", "") or "")]
    if tool_name == "Edit":
        return [("new_string", tool_input.get("new_string", "") or "")]
    if tool_name == "MultiEdit":
        return [
            (f"edits[{i}].new_string", e.get("new_string", "") or "")
            for i, e in enumerate(tool_input.get("edits", []) or [])
        ]
    return []


def check_non_ascii(path, texts):
    for label, text in texts:
        for lineno, line in enumerate(text.splitlines(), 1):
            for col, ch in enumerate(line, 1):
                if ord(ch) > 0x7F:
                    block(
                        "style",
                        f"non-ASCII character U+{ord(ch):04X} ({ch!r}) in {path} "
                        f"({label} line {lineno} col {col}). Use plain ASCII: "
                        f"'-' not en/em-dash, '->' not arrow glyphs, straight quotes.",
                    )


def check_future_annotations(path, texts):
    if path.suffix != ".py":
        return
    pattern = re.compile(r"^\s*from\s+__future__\s+import\s+annotations", re.M)
    for label, text in texts:
        if pattern.search(text):
            block(
                "style",
                f"'from __future__ import annotations' in {path} ({label}). The "
                f"compiler omits it. Write forward refs as string literals, "
                f'e.g. inner: "TypeRef".',
            )


def check_template_comments(path, texts):
    if "compiler/cpp/templates" not in str(path).replace("\\", "/"):
        return
    for label, text in texts:
        # Blank out Jinja spans (keeping newlines) so `//` inside {# #}, {{ }}, or
        # {% %} -- none of which reach the generated C++ -- is not mistaken for an
        # emitted comment, while line and column numbers stay accurate.
        scrubbed = _JINJA.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)
        for lineno, line in enumerate(scrubbed.splitlines(), 1):
            idx = line.find("//")
            if idx == -1:
                continue
            # namespace close-markers are the only `//` allowed in emitted output
            if "namespace" in line[idx:]:
                continue
            block(
                "style",
                f"'//' comment emitted into generated header from {path} "
                f"({label} line {lineno}). Templates must not write prose comments "
                f"into C++ output. Put notes in a Jinja {{# ... #}} block instead. "
                f"Only '}}  // namespace ...' close-markers are allowed.",
            )


def check_commit_coauthor(tool_input):
    command = tool_input.get("command", "") or ""
    if "git commit" not in command:
        return
    if re.search(r"co-authored-by", command, re.I):
        block(
            "style",
            "this commit adds a 'Co-Authored-By' trailer. This repo never credits "
            "Claude as a co-author. Remove the trailer.",
        )


def run_ruff(path):
    if path.suffix != ".py" or not path.is_file():
        return
    runners = (
        ["ruff", "check", str(path)],
        ["uv", "run", "--no-project", "--with", "ruff", "ruff", "check", str(path)],
    )
    for argv in runners:
        try:
            proc = subprocess.run(argv, capture_output=True, text=True)
        except FileNotFoundError:
            continue
        if proc.returncode == 0:
            return
        if proc.returncode == 1:  # ruff's "violations found" exit code
            out = (proc.stdout + proc.stderr).strip()
            block("style", f"ruff check found issues in {path}:\n{out}")
        # returncode >= 2 means ruff failed to start; try the next runner
    # ruff unavailable everywhere: do not block on tooling absence


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if event == "PreToolUse":
        if tool_name == "Bash":
            check_commit_coauthor(tool_input)
            return
        if tool_name in EDIT_TOOLS:
            path = Path(tool_input.get("file_path", "") or "unknown")
            texts = candidate_texts(tool_name, tool_input)
            check_non_ascii(path, texts)
            check_future_annotations(path, texts)
            check_template_comments(path, texts)
        return

    if event == "PostToolUse" and tool_name in EDIT_TOOLS:
        raw = tool_input.get("file_path", "") or ""
        if raw:
            run_ruff(Path(raw))


if __name__ == "__main__":
    main()
