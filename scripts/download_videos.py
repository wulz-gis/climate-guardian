"""视频下载与元数据旁注生成脚本。

本脚本读取 `assets/videos/lesson-key-video-links.csv` 与 `assets/videos/link-health.csv`，
尝试下载可获取的视频文件（优先使用直接 MP4 链接），并在输出文件旁生成元数据 JSON。

使用约束：仅用于教学目的，不用于商业用途；请遵守来源站点的使用条款与版权声明。

运行示例：
    python3 scripts/download_videos.py --outdir assets/videos/downloads --overwrite

参数说明：
    --csv PATH         指定关键视频链接CSV（默认：assets/videos/lesson-key-video-links.csv）
    --health PATH      指定链接健康检查CSV（默认：assets/videos/link-health.csv）
    --outdir PATH      下载输出目录（默认：assets/videos/downloads）
    --overwrite        若目标文件存在，则备份后覆盖（默认：跳过）
    --use-yt-dlp       允许使用 yt-dlp 处理页面/YouTube链接（若本机已安装）
    --dry-run          仅打印将要执行的下载计划，不实际下载

PEP 257: 全部函数采用规范文档字符串；函数级注释说明核心逻辑。
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ------------------------------ 常量与工具函数 ------------------------------

DEFAULT_CSV = os.path.join("assets", "videos", "lesson-key-video-links.csv")
DEFAULT_HEALTH = os.path.join("assets", "videos", "link-health.csv")
DEFAULT_OUTDIR = os.path.join("assets", "videos", "downloads")


def ensure_dir(path: str) -> None:
    """确保目录存在。

    Args:
        path: 目录路径。
    """

    os.makedirs(path, exist_ok=True)


def backup_if_exists(path: str) -> Optional[str]:
    """如目标存在则以时间戳备份并返回备份路径。

    Args:
        path: 目标文件路径。

    Returns:
        备份文件路径；若原文件不存在则返回 None。
    """

    if os.path.exists(path):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        bak = f"{path}.bak-{ts}"
        os.rename(path, bak)
        return bak
    return None


def compute_sha256(path: str) -> str:
    """计算文件的SHA256校验值。

    Args:
        path: 文件路径。

    Returns:
        十六进制字符串形式的SHA256校验值。
    """

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_with_backup(out_path: str, obj: Dict) -> str:
    """写出 JSON 内容；如目标存在则先备份后覆盖。

    Args:
        out_path: 输出 JSON 路径。
        obj: 要写出的对象（会进行缩进格式化）。

    Returns:
        最终写出的 JSON 路径。
    """

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bak = backup_if_exists(out_path)
    if bak:
        print(f"已备份现有文件 -> {bak}")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return out_path


def is_command_available(cmd: str) -> bool:
    """检测命令是否在系统中可用。"""

    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """生成适合文件系统的安全文件名。

    Args:
        name: 原始名称（如视频标题）。

    Returns:
        经过清理后的文件名片段。
    """

    keep = re.sub(r"[^\w\-\s]", "", name, flags=re.UNICODE)
    keep = keep.strip().replace(" ", "-")
    return re.sub(r"-+", "-", keep)[:120]


# ------------------------------ 数据模型 ------------------------------

@dataclass
class VideoEntry:
    """视频条目信息，来自CSV合并解析。"""

    lesson: str
    title: str
    source: str
    rights_holder: Optional[str]
    page_url: str
    duration_min: Optional[str]
    quality: Optional[str]
    notes: Optional[str]
    health_code: Optional[str]

    def direct_mp4_url(self) -> Optional[str]:
        """尝试从 notes 提取直接MP4链接。"""

        if not self.notes:
            return None
        m = re.search(r"Direct\s+MP4\s+available:\s*(https?://[^\s]+\.mp4)", self.notes, flags=re.IGNORECASE)
        return m.group(1) if m else None


# ------------------------------ CSV 解析 ------------------------------

def read_csv_rows(path: str) -> List[Dict[str, str]]:
    """读取CSV为字典行列表。"""

    rows: List[Dict[str, str]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def merge_video_entries(key_rows: List[Dict[str, str]], health_rows: List[Dict[str, str]]) -> List[VideoEntry]:
    """合并两个CSV的条目为 VideoEntry 列表。

    合并键：`lesson` + `url`。
    优先以关键链接CSV的字段为准，补充 `http_code` 与健康备注。
    """

    health_index: Dict[Tuple[str, str], Dict[str, str]] = {}
    for h in health_rows:
        key = (h.get("lesson", ""), h.get("url", ""))
        health_index[key] = h

    entries: List[VideoEntry] = []
    for r in key_rows:
        key = (r.get("lesson", ""), r.get("url", ""))
        h = health_index.get(key, {})
        entries.append(
            VideoEntry(
                lesson=r.get("lesson", "").strip(),
                title=r.get("title", "").strip(),
                source=r.get("source", "").strip(),
                rights_holder=(r.get("rights_holder") or "").strip() or None,
                page_url=r.get("url", "").strip(),
                duration_min=(r.get("duration_estimate_min") or "").strip() or None,
                quality=(r.get("quality") or "").strip() or None,
                notes=(r.get("notes") or "").strip() or None,
                health_code=(h.get("http_code") or "").strip() or None,
            )
        )
    return entries


# ------------------------------ 下载实现 ------------------------------

def download_with_curl(url: str, out_path: str) -> bool:
    """使用 curl 下载文件。

    Args:
        url: 下载链接（建议为MP4直链）。
        out_path: 输出文件路径。

    Returns:
        下载是否成功。
    """

    ensure_dir(os.path.dirname(out_path))
    backup_if_exists(out_path)
    cmd = [
        "curl",
        "-L",
        "--retry", "3",
        "--retry-delay", "2",
        "-o", out_path,
        url,
    ]
    print("执行:", " ".join(shlex.quote(c) for c in cmd))
    res = subprocess.run(cmd)
    return res.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0


def download_with_ytdlp(url: str, out_dir: str, base_name: str) -> Optional[str]:
    """使用 yt-dlp 下载页面/YouTube视频。

    Args:
        url: 页面或 YouTube 链接。
        out_dir: 输出目录。
        base_name: 基础文件名（不含扩展名）。

    Returns:
        成功下载后的文件路径；失败返回 None。
    """

    if not is_command_available("yt-dlp"):
        return None
    ensure_dir(out_dir)
    # 让 yt-dlp 选择最佳格式，并以 base_name 命名（自动加扩展名）
    template = os.path.join(out_dir, base_name + ".%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "-o", template,
        url,
    ]
    print("执行:", " ".join(shlex.quote(c) for c in cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        return None
    # 尝试在目录中寻找以 base_name 开头的文件
    for fn in os.listdir(out_dir):
        if fn.startswith(base_name + "."):
            return os.path.join(out_dir, fn)
    return None


def write_video_sidecar(out_path: str, entry: VideoEntry, download_url: str) -> str:
    """为下载的视频写旁注元数据 JSON。"""

    meta = {
        "lesson": entry.lesson,
        "title": entry.title,
        "source": entry.source,
        "rights_holder": entry.rights_holder,
        "original_page_url": entry.page_url,
        "download_url": download_url,
        "duration_estimate_min": entry.duration_min,
        "quality": entry.quality,
        "sha256": compute_sha256(out_path) if os.path.exists(out_path) else None,
        "use_restrictions": "仅用于教学用途，非商业使用；遵守来源站点使用条款。",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    sidecar = out_path + ".metadata.json"
    return write_json_with_backup(sidecar, meta)


def write_url_placeholder(out_dir: str, base_name: str, entry: VideoEntry) -> str:
    """无法直接下载时，写出 .url 占位文件与元数据，便于后续人工获取。"""

    ensure_dir(out_dir)
    url_file = os.path.join(out_dir, base_name + ".url")
    backup_if_exists(url_file)
    with open(url_file, "w", encoding="utf-8") as f:
        f.write(entry.page_url + "\n")
    # 旁注包含不可下载说明
    meta = {
        "lesson": entry.lesson,
        "title": entry.title,
        "source": entry.source,
        "rights_holder": entry.rights_holder,
        "original_page_url": entry.page_url,
        "download_url": None,
        "http_code": entry.health_code,
        "note": "链接不可直接下载或受限制，已生成占位 .url 文件以供课前下载准备。",
        "use_restrictions": "仅用于教学用途，非商业使用；遵守来源站点使用条款。",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    sidecar = url_file + ".metadata.json"
    write_json_with_backup(sidecar, meta)
    return url_file


# ------------------------------ 主流程 ------------------------------

def plan_and_download(csv_path: str, health_path: str, out_dir: str, overwrite: bool, use_ytdlp: bool, dry_run: bool) -> List[str]:
    """读取CSV、制定下载计划并执行下载。

    返回已生成的输出文件列表（视频文件或 .url 占位文件）。
    """

    ensure_dir(out_dir)

    key_rows = read_csv_rows(csv_path)
    health_rows = read_csv_rows(health_path) if os.path.exists(health_path) else []
    entries = merge_video_entries(key_rows, health_rows)

    outputs: List[str] = []
    for e in entries:
        base = f"lesson-{e.lesson}-{sanitize_filename(e.title)}"
        mp4_direct = e.direct_mp4_url()
        target_mp4 = os.path.join(out_dir, base + ".mp4")

        if os.path.exists(target_mp4) and not overwrite:
            print(f"跳过（已存在且不覆盖）：{target_mp4}")
            outputs.append(target_mp4)
            continue

        if mp4_direct:
            print(f"检测到直接MP4链接：{mp4_direct}")
            if dry_run:
                print(f"DRY-RUN: 计划下载 -> {mp4_direct} -> {target_mp4}")
                outputs.append(target_mp4)
                continue
            ok = download_with_curl(mp4_direct, target_mp4)
            if ok:
                write_video_sidecar(target_mp4, e, mp4_direct)
                outputs.append(target_mp4)
            else:
                print(f"下载失败，生成占位：{e.page_url}")
                outputs.append(write_url_placeholder(out_dir, base, e))
            continue

        # 无直接MP4：可选使用 yt-dlp
        if use_ytdlp:
            if dry_run:
                print(f"DRY-RUN: 计划使用 yt-dlp 下载 -> {e.page_url}")
                outputs.append(target_mp4)
                continue
            saved = download_with_ytdlp(e.page_url, out_dir, base)
            if saved and os.path.exists(saved):
                write_video_sidecar(saved, e, e.page_url)
                outputs.append(saved)
                continue

        # 仍不可下载：生成占位
        print(f"不可直接下载或受限制，生成占位 .url -> {e.page_url}")
        outputs.append(write_url_placeholder(out_dir, base, e))

    return outputs


def main(argv: List[str] | None = None) -> None:
    """命令行入口：解析参数并执行下载任务。"""

    import argparse

    parser = argparse.ArgumentParser(description="下载教学视频并生成元数据旁注")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="关键视频链接CSV路径")
    parser.add_argument("--health", default=DEFAULT_HEALTH, help="链接健康检查CSV路径")
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR, help="下载输出目录")
    parser.add_argument("--overwrite", action="store_true", help="备份后覆盖已存在文件")
    parser.add_argument("--use-yt-dlp", action="store_true", help="允许使用yt-dlp处理页面/YouTube链接")
    parser.add_argument("--dry-run", action="store_true", help="仅打印计划，不实际下载")

    args = parser.parse_args(argv if argv is not None else None)

    print(f"输入CSV: {args.csv}")
    print(f"健康CSV: {args.health}")
    print(f"输出目录: {args.outdir}")
    print(f"覆盖模式: {'是' if args.overwrite else '否'}")
    print(f"使用yt-dlp: {'是' if args.use_yt_dlp else '否'} (检测: {'可用' if is_command_available('yt-dlp') else '不可用'})")
    print(f"Dry Run: {'是' if args.dry_run else '否'}")

    outputs = plan_and_download(
        csv_path=args.csv,
        health_path=args.health,
        out_dir=args.outdir,
        overwrite=args.overwrite,
        use_ytdlp=args.use_yt_dlp,
        dry_run=args.dry_run,
    )

    print("\n任务完成，输出摘要：")
    for p in outputs:
        print(f"- {p}")


if __name__ == "__main__":
    main()