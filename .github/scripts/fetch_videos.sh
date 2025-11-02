#!/usr/bin/env bash
# 统一包装器：在 CI 中使用 Python 下载器按 CSV 下载视频并生成元数据
# 容错：如 Python 或依赖不可用，仅输出提示并不中断其他步骤
set -u

# 仅在 CI 环境执行
if [[ "${CI:-false}" != "true" ]]; then
  echo "Skip video fetch (CI not set)"
  exit 0
fi

VID_DIR="climate-guardian/public/assets/videos"
CSV="assets/videos/lesson-key-video-links.csv"
HEALTH="assets/videos/link-health.csv"

mkdir -p "$VID_DIR"

# 版本与环境信息
python -V || true
pip show yt-dlp || true
command -v yt-dlp && yt-dlp --version || true

# 使用 Python 下载器；如失败，打印错误但不退出
set +e
python scripts/download_videos.py \
  --csv "$CSV" \
  --health "$HEALTH" \
  --outdir "$VID_DIR" \
  --overwrite \
  --use-yt-dlp
status=$?
set -e

if [[ $status -ne 0 ]]; then
  echo "Warn: Python downloader returned non-zero status: $status" >&2
fi

# 调试：列出目录与文件摘要
ls -lah "$VID_DIR" || true
find "$VID_DIR" -maxdepth 1 -type f -name "*.mp4" -print || true
find "$VID_DIR" -maxdepth 1 -type f -name "*.metadata.json" -print || true

echo "All videos ready via Python downloader."