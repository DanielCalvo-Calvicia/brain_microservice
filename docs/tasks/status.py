"""Shows where the Brain restructure stands and what to do next.

    windows\\Scripts\\python.exe docs\\tasks\\status.py            print the table and the NEXT subtask
    windows\\Scripts\\python.exe docs\\tasks\\status.py --write    also refresh the table inside docs/tasks/README.md

It reads only the `Status:` line of every `docs/tasks/T*/S*.md`. Standard library only.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = re.compile(r"^Status:\s*(TODO|IN PROGRESS|DONE|BLOCKED)\b", re.M)
TITLE = re.compile(r"^#\s*(T\d+-S\d+):\s*(.+)$", re.M)
MARK = {"DONE": "[x]", "IN PROGRESS": "[~]", "BLOCKED": "[!]", "TODO": "[ ]"}


def load():
    tasks = []
    for task_dir in sorted(d for d in os.listdir(HERE) if re.match(r"T\d+-", d) and os.path.isdir(os.path.join(HERE, d))):
        subtasks = []
        for name in sorted(f for f in os.listdir(os.path.join(HERE, task_dir)) if re.match(r"S\d+-.*\.md$", f)):
            path = os.path.join(HERE, task_dir, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            status = STATUS.search(text)
            title = TITLE.search(text)
            subtasks.append({
                "file": f"{task_dir}/{name}",
                "id": title.group(1) if title else name,
                "title": title.group(2).strip() if title else name,
                "status": status.group(1) if status else "TODO",
            })
        tasks.append((task_dir, subtasks))
    return tasks


def render(tasks):
    lines = []
    for task_dir, subtasks in tasks:
        done = sum(1 for s in subtasks if s["status"] == "DONE")
        lines.append(f"**{task_dir}**  ({done}/{len(subtasks)} done)")
        for s in subtasks:
            lines.append(f"  {MARK[s['status']]} {s['id']}  {s['title']}  [{s['status']}]  ->  docs/tasks/{s['file']}")
        lines.append("")
    pending = [s for _, subs in tasks for s in subs if s["status"] != "DONE"]
    total = sum(len(subs) for _, subs in tasks)
    lines.append(f"{total - len(pending)}/{total} subtasks done.")
    if pending:
        nxt = pending[0]
        lines.append(f"NEXT: {nxt['id']}  {nxt['title']}  [{nxt['status']}]  ->  docs/tasks/{nxt['file']}")
        blocked = [s["id"] for s in pending if s["status"] == "BLOCKED"]
        if blocked:
            lines.append("BLOCKED: " + ", ".join(blocked))
    else:
        lines.append("Everything is done.")
    return "\n".join(lines)


def markdown_table(tasks):
    rows = ["| Subtask | Title | Status |", "|---|---|---|"]
    for task_dir, subtasks in tasks:
        rows.append(f"| **{task_dir}** | | {sum(1 for s in subtasks if s['status'] == 'DONE')}/{len(subtasks)} |")
        for s in subtasks:
            rows.append(f"| [{s['id']}]({s['file']}) | {s['title']} | {s['status']} |")
    return "\n".join(rows)


def main():
    tasks = load()
    print(render(tasks))
    if "--write" in sys.argv:
        path = os.path.join(HERE, "README.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        pattern = re.compile(r"(<!-- STATUS:START -->).*?(<!-- STATUS:END -->)", re.S)
        if not pattern.search(text):
            sys.exit("README.md has no STATUS markers")
        text = pattern.sub(lambda m: m.group(1) + "\n" + markdown_table(tasks) + "\n" + m.group(2), text)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("README.md table refreshed")


if __name__ == "__main__":
    main()
