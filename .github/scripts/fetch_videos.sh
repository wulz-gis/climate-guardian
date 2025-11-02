#!/usr/bin/env bash
# 容错：不因单个下载失败而退出，仅保留未设置变量时报错
set -u

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
  if [[ -f "$f" ]]; then
    echo "Skip existing $f"
    continue
  fi
  echo "Downloading $(basename "$u")"
  # 使用失败不退出策略，且清理可能生成的空文件
  if ! curl -fL --retry 3 --retry-delay 2 --max-time 120 -o "$f" "$u"; then
    echo "Warn: failed to download $u" >&2
    rm -f "$f"
    continue
  fi
  # 基于大小过滤明显的错误下载（<1KB）
  size=$(wc -c < "$f" 2>/dev/null || echo 0)
  if [[ ${size:-0} -lt 1024 ]]; then
    echo "Warn: file too small ($size bytes), removing: $f" >&2
    rm -f "$f"
    continue
  fi
  echo "Saved $f (${size} bytes)"

done

echo "All videos ready."