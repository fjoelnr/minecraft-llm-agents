import sys
import re
import pathlib


def extract(changelog_path: pathlib.Path, version: str) -> str:
    text = changelog_path.read_text(encoding="utf-8")
    # Normalize version if tag has a leading 'v'
    ver = version[1:] if version.startswith("v") else version

    # Match '## [X.Y.Z]' headings and capture content until next '## [' or end
    pattern = re.compile(
        rf"^##\s*\[{re.escape(ver)}\].*?$([\s\S]*?)(?=^\s*##\s*\[|\Z)", re.MULTILINE
    )
    m = pattern.search(text)
    if not m:
        # fallback: try plain '## X.Y.Z'
        pattern2 = re.compile(
            rf"^##\s*{re.escape(ver)}.*?$([\s\S]*?)(?=^\s*##\s*|\Z)", re.MULTILINE
        )
        m = pattern2.search(text)
    if not m:
        print(f"⚠️  Version {ver} not found in CHANGELOG.md", file=sys.stderr)
        # return top section as fallback
        return text

    content = m.group(1).strip()
    header = f"## {version}\n"
    return f"{header}\n{content}\n"


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_changelog.py <version>", file=sys.stderr)
        sys.exit(1)
    version = sys.argv[1]
    path = pathlib.Path("CHANGELOG.md")
    if not path.exists():
        print("CHANGELOG.md not found", file=sys.stderr)
        sys.exit(1)
    print(extract(path, version))


if __name__ == "__main__":
    main()
