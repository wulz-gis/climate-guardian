#!/usr/bin/env bash
set -euo pipefail

# 仅在 CI 环境执行
if [[ "${CI:-false}" != "true" ]]; then
  echo "Skip video fetch (CI not set)"
  exit 0
fi

VID_DIR="climate-guardian/public/assets/videos"
mkdir -p "$VID_DIR"

echo "Downloading intro videos…"
# 示例：第 17–25 课需要 9 个 30 s 以内 MP4（可扩展）
urls=(
  "https://github.com/user-assets/lesson-17-intro.mp4"
  "https://github.com/user-assets/lesson-18-intro.mp4"
  "https://github.com/user-assets/lesson-19-intro.mp4"
  "https://github.com/user-assets/lesson-20-intro.mp4"
  "https://github.com/user-assets/lesson-21-intro.mp4"
  "https://github.com/user-assets/lesson-22-intro.mp4"
  "https://github.com/user-assets/lesson-23-intro.mp4"
  "https://github.com/user-assets/lesson-24-intro.mp4"
  "https://github.com/user-assets/lesson-25-intro.mp4"
)

for u in "${urls[@]}"; do
  f="$VID_DIR/$(basename "$u")"
  if [[ ! -f "$f" ]]; then
    curl -L -o "$f" "$u"
  else
    echo "Skip existing $f"
  fi
done

echo "All videos ready."