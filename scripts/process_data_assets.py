"""
数据处理脚本：将已下载的真实数据加工为教学用CSV与图像资产。

功能概览：
- 读取 NASA GISTEMP 全球温度异常（年均 J-D）
- 读取 NOAA Mauna Loa 月均 CO₂ 并计算年均
- 生成第12课（长期气温与滑动均值）教学用CSV
- 生成第21课（CO₂ 与温度异常关系）教学用CSV
- 生成示例图像：全球温度异常折线图、CO₂与温度双轴图

注意：本脚本遵循 PEP 257 文档字符串规范；函数级注释完整。
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple
import json
import hashlib
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import re
import xlrd

# macOS 中文字体配置（遵循规范）：
# 使用 Heiti TC 并处理负号显示问题，以避免中文标题/标签异常。
plt.rcParams['font.family'] = 'Heiti TC'
plt.rcParams['axes.unicode_minus'] = False


# 常量：路径定义
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "data")
ASSETS_DATA_DIR = os.path.join(BASE_DIR, "assets", "data")
ASSETS_IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")

GISTEMP_CSV = os.path.join(DATA_DIR, "gistemp_glb_ts_dsst.csv")
NOAA_CO2_MONTHLY_CSV = os.path.join(DATA_DIR, "noaa_mauna_loa_co2_monthly.csv")
SEA_LEVEL_ASCII = os.path.join(DATA_DIR, "nasa_gmsl_ascii.txt")
LESSON15_METADATA_JSON = os.path.join(ASSETS_DATA_DIR, "lesson-15-metadata.json")
SCHOOL_DIR = os.path.join(DATA_DIR, "曹杨中学")

# 第2/3课原始数据路径常量（真实科学数据来源，优先 NOAA/NCEI）：
ITRDB_RWL_CANA426 = os.path.join(DATA_DIR, "cana426-rwl-noaa.txt")
NGRIP_D18O_20YR = os.path.join(DATA_DIR, "vinther2006-gicc05-holocene-ngrip-20yr-noaa.txt")
SPELEO_XL16 = os.path.join(DATA_DIR, "xianglong2018-xl16-noaa.txt")
WALKER_GS = os.path.join(DATA_DIR, "walker2021gs.txt")

# 第2/3课元数据输出路径
LESSON02_METADATA_JSON = os.path.join(ASSETS_DATA_DIR, "lesson-02-metadata.json")
LESSON03_METADATA_JSON = os.path.join(ASSETS_DATA_DIR, "lesson-03-metadata.json")
RAW_SOURCES_METADATA_JSON = os.path.join(ASSETS_DATA_DIR, "raw-data-metadata.json")

def write_csv_with_backup(out_path: str, header: List[str], rows: List[List[str]]) -> str:
    """写入 CSV 文件；如目标存在则先备份后覆盖。

    Args:
        out_path: 输出 CSV 路径。
        header: 列名列表。
        rows: 行数据列表（每行为同长度的列值）。

    Returns:
        最终写出的 CSV 路径。
    """

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        bak = f"{out_path}.bak-{ts}"
        os.rename(out_path, bak)
        print(f"已备份现有文件 -> {bak}")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return out_path


def write_json_with_backup(out_path: str, obj: Dict) -> str:
    """写 JSON 文件（如已存在则自动备份）。

    Args:
        out_path: 目标 JSON 路径。
        obj: 可序列化的字典对象。

    Returns:
        最终写入的 JSON 路径。
    """

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        backup_path = f"{out_path}.bak-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            os.rename(out_path, backup_path)
            print(f"已备份现有文件 -> {backup_path}")
        except Exception as e:
            print(f"警告：无法备份 {out_path} -> {e}")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return out_path


# ===== 第2/3课数据结构与解析函数 =====

@dataclass
class AnnualTreeRingRecord:
    """树轮年序列记录。

    Attributes:
        year: 年份（公元年份，CE）
        ring_width_mm: 年度树轮宽度（mm），对同年多核心取均值。
    """

    year: int
    ring_width_mm: float


@dataclass
class IceCoreRecord:
    """冰芯 δ18O 年序列记录。

    Attributes:
        year: 年份（公元年份，CE）。由 b2k 年代转换：year = 2000 - age_b2k。
        d18o_permille: δ18O（‰，VPDB/SMOW，按文件给定）。
    """

    year: int
    d18o_permille: float


@dataclass
class SpeleothemGrowthRecord:
    """石笋生长速率记录。

    Attributes:
        site: 样点/洞穴名称（如 "Xianglong XL-16"）。
        year: 年份（CE）。由 BP1950 年代转换：year = 1950 - age_BP。
        growth_mm_per_yr: 生长速率（mm/yr）。
    """

    site: str
    year: int
    growth_mm_per_yr: float


@dataclass
class CoreGrainSizeRecord:
    """湖泊/海洋岩芯粒度记录。

    Attributes:
        site: 样点/湖泊名称（如 "Lake Walker"）。
        year: 年份（CE）。由 Varve 年代（BP）上下界取中值并转换：year = 1950 - ((BP_minus + BP_plus)/2)。
        d50_um: 中值粒径 D50（µm）。
    """

    site: str
    year: int
    d50_um: float


def parse_itrdb_rwl_template(path: str) -> List[AnnualTreeRingRecord]:
    """解析 NOAA/NCEI ITRDB 模板格式的树轮原始测量（rwl-noaa.txt）。

    解析策略：
    - 跳过以 "#" 开头的元数据头部行。
    - 数据段为制表符或空白分隔；首列为 `age_CE`（公元年份），其后为多条核心的年度宽度（单位 mm）。
    - 对同一年份的所有数值取算术平均（过滤缺失，如 "NaN"、空字符串）。

    Args:
        path: ITRDB 模板文本文件路径。

    Returns:
        年度树轮宽度记录列表（mm）。
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到树轮数据文件: {path}")

    yearly_values: Dict[int, List[float]] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p for p in line.split("\t") if p != ""] if "\t" in line else [p for p in line.split() if p != ""]
            if not parts:
                continue
            # 年份
            try:
                year = int(float(parts[0]))
            except Exception:
                continue
            # 收集该年所有数值列
            values: List[float] = []
            for p in parts[1:]:
                s = p.strip()
                if not s or s.lower() in {"nan", "na"}:
                    continue
                try:
                    values.append(float(s))
                except ValueError:
                    continue
            if values:
                yearly_values.setdefault(year, []).extend(values)

    records: List[AnnualTreeRingRecord] = []
    for y, vals in sorted(yearly_values.items()):
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        records.append(AnnualTreeRingRecord(year=y, ring_width_mm=float(avg)))
    return records


def parse_vinther_ngrip_20yr(path: str) -> List[IceCoreRecord]:
    """解析 Vinther et al. (2006) GICC05 Holocene 20年分辨率 δ18O 数据。

    文件列通常为（按照 NOAA 模板表头）：
    0: iceage_BP2k（b2k 年代）、1: iceage_BP1950、2: depth_ngrip1_m、3: d18O_ngrip1、
    4: depth_ngrip2_m、5: d18O_ngrip2、6: iceage_err。
    因此 δ18O 列为索引 3 或 5；优先使用 d18O_ngrip1（索引 3），若缺失再回退到索引 5。
    年份转换遵循 b2k 约定：year_CE = 2000 - age_b2k。

    Args:
        path: NGRIP Holocene 20年分辨率文本路径。

    Returns:
        冰芯 δ18O 年记录列表（CE、‰）。
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到冰芯数据文件: {path}")

    records: List[IceCoreRecord] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p for p in line.replace("\t", " ").split() if p]
            if not parts:
                continue
            # 年代（b2k）
            try:
                age_b2k = float(parts[0])
            except ValueError:
                continue
            # δ18O 列：优先 3 (d18O_ngrip1)，回退 5 (d18O_ngrip2)
            d18o: float | None = None
            for idx in (3, 5):
                if idx < len(parts):
                    try:
                        val = float(parts[idx])
                        if not (val != val):  # 不是 NaN
                            d18o = val
                            break
                    except ValueError:
                        pass
            if d18o is None:
                continue
            year_ce = int(round(2000 - age_b2k))
            records.append(IceCoreRecord(year=year_ce, d18o_permille=float(d18o)))
    return records


def parse_speleothem_xl16_growth(path: str, site_label: str = "Xianglong XL-16") -> List[SpeleothemGrowthRecord]:
    """解析 Xianglong Cave XL-16 石笋生长速率（mm/yr）。

    NOAA 模板文件包含变量 `Age`（calendar year before present）与 `GR`（growth rate, mm/yr）。
    按常规 Paleoclimate 约定，将 BP 参考年视为 1950：year_CE = 1950 - age_BP。

    Args:
        path: 石笋模板文本路径。
        site_label: 样点标签（默认 "Xianglong XL-16"）。

    Returns:
        石笋生长速率记录列表（CE、mm/yr）。
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到石笋数据文件: {path}")

    records: List[SpeleothemGrowthRecord] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p for p in line.split("\t") if p != ""] if "\t" in line else [p for p in line.split() if p != ""]
            if len(parts) < 3:
                # 期望至少包含 Age 与 GR 两列
                continue
            # 尝试在行中查找 Age 与 GR（鲁棒：取前两个数值作为 Age 与 GR）
            nums: List[float] = []
            for p in parts:
                try:
                    nums.append(float(p))
                except ValueError:
                    continue
            if len(nums) < 2:
                continue
            age_bp = nums[0]
            gr = nums[1]
            # 转换到 CE 年份
            year_ce = int(round(1950 - age_bp))
            records.append(SpeleothemGrowthRecord(site=site_label, year=year_ce, growth_mm_per_yr=float(gr)))
    return records


def parse_walker_grainsize(path: str, site_label: str = "Lake Walker") -> List[CoreGrainSizeRecord]:
    """解析 Lake Walker 晚全新世纹泥沉积物粒度（D50, µm）。

    文件包含 Varve 年龄上下界（`Varve_yearBP-`, `Varve_yearBP+`）与 D50（µm）。
    以上下界中值作为年代（BP），再转换为 CE：year_CE = 1950 - ((BP_minus + BP_plus)/2)。

    Args:
        path: 粒度文本路径。
        site_label: 样点标签（默认 "Lake Walker"）。

    Returns:
        岩芯粒度记录列表（CE、µm）。
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到岩芯粒度数据文件: {path}")

    records: List[CoreGrainSizeRecord] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Walker 文件为制表符或空白分隔，包含多粒度级别；首要提取 Varve 年龄与 D50
            parts = [p for p in line.split("\t") if p != ""] if "\t" in line else [p for p in line.split() if p != ""]
            # 搜集该行所有浮点数
            nums: List[float] = []
            for p in parts:
                try:
                    nums.append(float(p))
                except ValueError:
                    continue
            # 期望顺序：depth(mm), Varve_yearBP-, Varve_yearBP+, Thickness(mm), D50(µm), ...
            if len(nums) < 5:
                continue
            bp_minus = nums[1]
            bp_plus = nums[2]
            d50_um = nums[4]
            bp_mid = (bp_minus + bp_plus) / 2.0
            year_ce = int(round(1950 - bp_mid))
            records.append(CoreGrainSizeRecord(site=site_label, year=year_ce, d50_um=float(d50_um)))
    return records


def generate_lesson02_csv(tree_records: List[AnnualTreeRingRecord], ice_records: List[IceCoreRecord]) -> str:
    """生成第2课教学用 CSV：年份、宽度/mm、δ18O/‰。

    合并策略：
    - 冰芯为 20 年分辨率（CE 年份）。为获得交集，将树轮按 ±10 年窗口求均值，与冰芯年份对齐。
    - 过滤窗口内无树轮数据的年份。

    Args:
        tree_records: 树轮年序列（mm）。
        ice_records: 冰芯 δ18O 年序列（‰）。

    Returns:
        输出 CSV 路径 `assets/data/lesson-02-sample.csv`。
    """

    tree_map: Dict[int, float] = {r.year: r.ring_width_mm for r in tree_records}
    rows: List[List[object]] = []
    for ir in ice_records:
        y = ir.year
        window_vals: List[float] = []
        for yy in range(y - 10, y + 11):
            v = tree_map.get(yy)
            if isinstance(v, (int, float)):
                window_vals.append(float(v))
        if not window_vals:
            continue
        ring_mean = sum(window_vals) / len(window_vals)
        rows.append([y, round(ring_mean, 3), round(ir.d18o_permille, 3)])

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-02-sample.csv")
    write_csv_with_backup(out_path, ["年份", "宽度/mm", "δ18O/‰"], rows)
    return out_path


def generate_lesson03_csv(speleo_records: List[SpeleothemGrowthRecord], core_records: List[CoreGrainSizeRecord]) -> str:
    """生成第3课教学用 CSV：样点、年代、速率、粒度。

    输出两类样点：
    - 石笋：填写 `速率`（mm/yr），`粒度` 留空。
    - 岩芯：填写 `粒度`（µm），`速率` 留空。

    Args:
        speleo_records: 石笋生长速率记录列表。
        core_records: 岩芯粒度记录列表。

    Returns:
        输出 CSV 路径 `assets/data/lesson-03-sample.csv`。
    """

    rows: List[List[object]] = []
    for r in speleo_records:
        rows.append([r.site, r.year, round(r.growth_mm_per_yr, 3), ""])
    for r in core_records:
        rows.append([r.site, r.year, "", round(r.d50_um, 3)])
    # 按样点与年代排序，便于教学演示
    rows.sort(key=lambda x: (str(x[0]), int(x[1])))

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-03-sample.csv")
    write_csv_with_backup(out_path, ["样点", "年代", "速率", "粒度"], rows)
    return out_path


def write_lesson02_metadata(derived_csv: str) -> str:
    """写出第2课元数据 JSON，记录来源与许可信息。

    元数据包含：数据集短名/DOI/下载链接/本地路径/派生 CSV 等。
    """

    meta = {
        "sources": [
            {
                "type": "Tree Ring (ITRDB)",
                "dataset_short_name": "CANA426",
                "dataset_doi": None,
                "source_url": "https://www.ncei.noaa.gov/pub/data/paleo/treering/measurements/northamerica/canada/cana426-rwl-noaa.txt",
                "local_path": ITRDB_RWL_CANA426,
                "units": "ring width (mm)",
                "citation_guidelines_url": "https://www.ncei.noaa.gov/access/paleo-search/citation",
                "citation": f"NOAA NCEI, WDS Paleoclimatology: Tree Ring Measurements, site CANA426. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
            },
            {
                "type": "Ice Core (NGRIP)",
                "dataset_short_name": "GICC05 Holocene 20yr",
                "dataset_doi": "10.25921/pnba-f878",
                "publication_doi": "10.1029/2005JD006921",
                "source_url": "https://www.ncei.noaa.gov/pub/data/paleo/icecore/greenland/summit/ngrip/vinther2006-gicc05-holocene-ngrip-20yr-noaa.txt",
                "local_path": NGRIP_D18O_20YR,
                "units": "δ18O (‰)",
                "citation_guidelines_url": "https://www.ncei.noaa.gov/access/paleo-search/citation",
                "citation": f"NOAA NCEI, WDS Paleoclimatology: NGRIP Holocene δ18O (20-yr). Dataset DOI 10.25921/pnba-f878. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
            },
        ],
        "derived_csv": derived_csv,
        "download_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "license_note": "NOAA/WDS Paleoclimatology data; follow NOAA citation guidelines.",
    }
    return write_json_with_backup(LESSON02_METADATA_JSON, meta)


def write_lesson03_metadata(derived_csv: str) -> str:
    """写出第3课元数据 JSON，记录来源与许可信息。"""

    meta = {
        "sources": [
            {
                "type": "Speleothem",
                "dataset_short_name": "Xianglong XL-16",
                "dataset_doi": "10.25921/8d0j-jt40",
                "source_url": "https://www.ncei.noaa.gov/pub/data/paleo/speleothem/asia/china/xianglong2018-xl16-noaa.txt",
                "local_path": SPELEO_XL16,
                "units": "growth rate (mm/yr)",
                "citation_guidelines_url": "https://www.ncei.noaa.gov/access/paleo-search/citation",
                "citation": f"NOAA NCEI, WDS Paleoclimatology: Xianglong Cave XL-16 Speleothem Growth Rate. Dataset DOI 10.25921/8d0j-jt40. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
            },
            {
                "type": "Paleolimnology",
                "dataset_short_name": "Lake Walker Grain Size",
                "dataset_doi": "10.25921/9y0x-m754",
                "source_url": "https://www.ncei.noaa.gov/pub/data/paleo/paleolimnology/northamerica/canada/pq/walker2021gs.txt",
                "local_path": WALKER_GS,
                "units": "D50 (µm)",
                "citation_guidelines_url": "https://www.ncei.noaa.gov/access/paleo-search/citation",
                "citation": f"NOAA NCEI, WDS Paleoclimatology: Lake Walker Grain Size (D50). Dataset DOI 10.25921/9y0x-m754. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
            },
        ],
        "derived_csv": derived_csv,
        "download_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "license_note": "NOAA/WDS Paleoclimatology data; follow NOAA citation guidelines.",
    }
    return write_json_with_backup(LESSON03_METADATA_JSON, meta)


def write_raw_sources_metadata() -> str:
    """写出统一的原始数据元数据 JSON（包含来源与引用方式）。

    此元数据汇总 `data/data/` 下已存在的关键原始数据文件（GISTEMP、NOAA CO₂、海平面、树轮、冰芯、石笋、岩芯），
    提供：短名、类型、本地路径、来源URL、DOI、SHA256校验、推荐引用文本与引用指南链接。

    Returns:
        `assets/data/raw-data-metadata.json` 路径。
    """

    sources: List[Dict[str, str]] = []

    def add_source_if_exists(short: str, typ: str, local: str, url: str | None, dataset_doi: str | None, citation: str, citation_url: str | None = None):
        if not os.path.exists(local):
            return
        entry = {
            "dataset_short_name": short,
            "type": typ,
            "local_path": local,
            "source_url": url,
            "dataset_doi": dataset_doi,
            "sha256": compute_sha256(local) if os.path.isfile(local) else None,
            "citation": citation,
        }
        if citation_url:
            entry["citation_guidelines_url"] = citation_url
        sources.append(entry)

    # NASA GISTEMP（参考页面与推荐引用）
    add_source_if_exists(
        short="GISTEMP_v4",
        typ="Temperature (Anomaly)",
        local=GISTEMP_CSV,
        url="https://data.giss.nasa.gov/gistemp/",
        dataset_doi=None,
        citation=f"GISTEMP Team: GISS Surface Temperature Analysis (GISTEMP v4), NASA GISS. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://data.giss.nasa.gov/gistemp/faq/",
    )

    # NOAA Mauna Loa CO₂（参考页面）
    add_source_if_exists(
        short="NOAA_MaunaLoa_CO2_monthly",
        typ="CO₂ (ppm, monthly)",
        local=NOAA_CO2_MONTHLY_CSV,
        url="https://gml.noaa.gov/ccgg/trends/",
        dataset_doi=None,
        citation=f"NOAA Global Monitoring Laboratory (GML): Mauna Loa CO₂ monthly average. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://gml.noaa.gov/ccgg/trends/",
    )

    # NASA/NOAA 海平面（PO.DAAC 数据集）
    add_source_if_exists(
        short="GMSL_ASCII_V52",
        typ="Sea Level (mm)",
        local=SEA_LEVEL_ASCII,
        url=(
            "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus/Protected/"
            "MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V52/merged_global_sea_level_v5.2.txt"
        ),
        dataset_doi="10.5067/GMSLM-TJ152",
        citation=f"NOAA/NASA PO.DAAC: Merged Global Mean Sea Level V5.2 (ASCII). DOI 10.5067/GMSLM-TJ152. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://podaac.jpl.nasa.gov/",
    )

    # ITRDB 树轮
    add_source_if_exists(
        short="ITRDB_CANA426",
        typ="Tree Ring Width (mm)",
        local=ITRDB_RWL_CANA426,
        url="https://www.ncei.noaa.gov/pub/data/paleo/treering/measurements/northamerica/canada/cana426-rwl-noaa.txt",
        dataset_doi=None,
        citation=f"NOAA NCEI WDS Paleoclimatology: Tree Ring Measurements CANA426. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    # NGRIP δ18O（20年分辨率）
    add_source_if_exists(
        short="NGRIP_Holocene_20yr",
        typ="Ice Core δ18O (‰)",
        local=NGRIP_D18O_20YR,
        url="https://www.ncei.noaa.gov/pub/data/paleo/icecore/greenland/summit/ngrip/vinther2006-gicc05-holocene-ngrip-20yr-noaa.txt",
        dataset_doi="10.25921/pnba-f878",
        citation=f"NOAA NCEI WDS Paleoclimatology: NGRIP Holocene δ18O (20 yr). DOI 10.25921/pnba-f878. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    # 石笋 XL-16
    add_source_if_exists(
        short="Xianglong_XL16",
        typ="Speleothem Growth Rate (mm/yr)",
        local=SPELEO_XL16,
        url="https://www.ncei.noaa.gov/pub/data/paleo/speleothem/asia/china/xianglong2018-xl16-noaa.txt",
        dataset_doi="10.25921/8d0j-jt40",
        citation=f"NOAA NCEI WDS Paleoclimatology: Xianglong Cave XL-16 growth rate. DOI 10.25921/8d0j-jt40. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    # Lake Walker 粒度
    add_source_if_exists(
        short="LakeWalker_D50",
        typ="Grain Size D50 (µm)",
        local=WALKER_GS,
        url="https://www.ncei.noaa.gov/pub/data/paleo/paleolimnology/northamerica/canada/pq/walker2021gs.txt",
        dataset_doi="10.25921/9y0x-m754",
        citation=f"NOAA NCEI WDS Paleoclimatology: Lake Walker grain size D50. DOI 10.25921/9y0x-m754. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    meta = {
        "download_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sources": sources,
    }
    return write_json_with_backup(RAW_SOURCES_METADATA_JSON, meta)


def write_raw_sidecar_metadata() -> List[str]:
    """为每个原始数据文件写旁注元数据到 `data/data` 目录。

    旁注文件命名形如：`<原始文件名>.metadata.json`，内容包含：短名、类型、本地路径、来源URL、DOI、
    SHA256、推荐引用与引用指南链接，以及 `created_at` 时间戳。

    Returns:
        已写入的旁注元数据文件路径列表。
    """

    written_paths: List[str] = []

    def add_source_if_exists(short: str, typ: str, local: str, url: str | None, dataset_doi: str | None, citation: str, citation_url: str | None = None):
        if not os.path.exists(local):
            return
        sidecar_path = f"{local}.metadata.json"
        obj = {
            "dataset_short_name": short,
            "type": typ,
            "local_path": local,
            "source_url": url,
            "dataset_doi": dataset_doi,
            "sha256": compute_sha256(local) if os.path.isfile(local) else None,
            "citation": citation,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if citation_url:
            obj["citation_guidelines_url"] = citation_url
        write_json_with_backup(sidecar_path, obj)
        written_paths.append(sidecar_path)

    # NASA GISTEMP
    add_source_if_exists(
        short="GISTEMP_v4",
        typ="Temperature (Anomaly)",
        local=GISTEMP_CSV,
        url="https://data.giss.nasa.gov/gistemp/",
        dataset_doi=None,
        citation=f"GISTEMP Team: GISS Surface Temperature Analysis (GISTEMP v4), NASA GISS. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://data.giss.nasa.gov/gistemp/faq/",
    )

    # NOAA Mauna Loa CO₂
    add_source_if_exists(
        short="NOAA_MaunaLoa_CO2_monthly",
        typ="CO₂ (ppm, monthly)",
        local=NOAA_CO2_MONTHLY_CSV,
        url="https://gml.noaa.gov/ccgg/trends/",
        dataset_doi=None,
        citation=f"NOAA Global Monitoring Laboratory (GML): Mauna Loa CO₂ monthly average. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://gml.noaa.gov/ccgg/trends/",
    )

    # 海平面（PO.DAAC）
    add_source_if_exists(
        short="GMSL_ASCII_V52",
        typ="Sea Level (mm)",
        local=SEA_LEVEL_ASCII,
        url=(
            "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus/Protected/"
            "MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V52/merged_global_sea_level_v5.2.txt"
        ),
        dataset_doi="10.5067/GMSLM-TJ152",
        citation=f"NOAA/NASA PO.DAAC: Merged Global Mean Sea Level V5.2 (ASCII). DOI 10.5067/GMSLM-TJ152. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://podaac.jpl.nasa.gov/",
    )

    # 树轮
    add_source_if_exists(
        short="ITRDB_CANA426",
        typ="Tree Ring Width (mm)",
        local=ITRDB_RWL_CANA426,
        url="https://www.ncei.noaa.gov/pub/data/paleo/treering/measurements/northamerica/canada/cana426-rwl-noaa.txt",
        dataset_doi=None,
        citation=f"NOAA NCEI WDS Paleoclimatology: Tree Ring Measurements CANA426. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    # NGRIP δ18O
    add_source_if_exists(
        short="NGRIP_Holocene_20yr",
        typ="Ice Core δ18O (‰)",
        local=NGRIP_D18O_20YR,
        url="https://www.ncei.noaa.gov/pub/data/paleo/icecore/greenland/summit/ngrip/vinther2006-gicc05-holocene-ngrip-20yr-noaa.txt",
        dataset_doi="10.25921/pnba-f878",
        citation=f"NOAA NCEI WDS Paleoclimatology: NGRIP Holocene δ18O (20 yr). DOI 10.25921/pnba-f878. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    # 石笋 XL-16
    add_source_if_exists(
        short="Xianglong_XL16",
        typ="Speleothem Growth Rate (mm/yr)",
        local=SPELEO_XL16,
        url="https://www.ncei.noaa.gov/pub/data/paleo/speleothem/asia/china/xianglong2018-xl16-noaa.txt",
        dataset_doi="10.25921/8d0j-jt40",
        citation=f"NOAA NCEI WDS Paleoclimatology: Xianglong Cave XL-16 growth rate. DOI 10.25921/8d0j-jt40. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    # Lake Walker 粒度
    add_source_if_exists(
        short="LakeWalker_D50",
        typ="Grain Size D50 (µm)",
        local=WALKER_GS,
        url="https://www.ncei.noaa.gov/pub/data/paleo/paleolimnology/northamerica/canada/pq/walker2021gs.txt",
        dataset_doi="10.25921/9y0x-m754",
        citation=f"NOAA NCEI WDS Paleoclimatology: Lake Walker grain size D50. DOI 10.25921/9y0x-m754. Accessed {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
        citation_url="https://www.ncei.noaa.gov/access/paleo-search/citation",
    )

    return written_paths

def _extract_degree(text: str | float | int) -> float | None:
    """从类似 'ESE (123)' 文本中提取角度数值。

    支持直接数值或包含括号的方位文本；失败返回 None。
    """
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text)
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None

def _to_float(val: str | float | int) -> float | None:
    """尽可能将值转换为浮点数；失败返回 None。"""
    if isinstance(val, (int, float)):
        return float(val)
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "-", "NaN"):
        return None
    try:
        return float(s)
    except Exception:
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else None

def read_school_xls_rows(dir_path: str) -> List[Dict[str, str | float]]:
    """读取“曹杨中学”目录下所有 .xls，提取核心字段。

    提取字段：观测时间、气温(℃)、瞬时风向(°)、瞬时风速(m/s)、小时雨量(mm)。

    Args:
        dir_path: 学校数据目录路径。

    Returns:
        记录列表，每条记录包含：
        - time: 字符串时间（YYYY-MM-DD HH:MM）
        - temp_c: 浮点数气温（℃）
        - wind_dir_deg: 浮点数风向（度）
        - wind_speed_ms: 浮点数风速（m/s）
        - rain_hour_mm: 浮点数小时雨量（mm）
    """

    records: List[Dict[str, str | float]] = []
    if not os.path.isdir(dir_path):
        return records
    for name in sorted(os.listdir(dir_path)):
        if not name.lower().endswith(".xls"):
            continue
        path = os.path.join(dir_path, name)
        try:
            book = xlrd.open_workbook(path)
            sheet = book.sheet_by_index(0)
        except Exception as e:
            print(f"警告：无法打开 {path} -> {e}")
            continue

        header = sheet.row_values(0)
        # 映射列索引
        def idx(label: str) -> int | None:
            for i, h in enumerate(header):
                if str(h).strip().startswith(label):
                    return i
            return None

        i_time = idx("观测时间")
        i_temp = idx("气温(℃)")
        i_wdir = idx("瞬时风向(°)")
        i_wspd = idx("瞬时风速(m/s)")
        i_rain = idx("小时雨量(mm)")

        for r in range(1, sheet.nrows):
            row = sheet.row_values(r)
            time = row[i_time] if i_time is not None else None
            temp = _to_float(row[i_temp]) if i_temp is not None else None
            wdir = _extract_degree(row[i_wdir]) if i_wdir is not None else None
            wspd = _to_float(row[i_wspd]) if i_wspd is not None else None
            rain = _to_float(row[i_rain]) if i_rain is not None else None

            # 过滤缺失或异常值
            if isinstance(time, str) and time.strip():
                rec: Dict[str, str | float] = {
                    "time": time.strip(),
                }
                if isinstance(temp, (int, float)):
                    rec["temp_c"] = float(temp)
                if isinstance(wdir, (int, float)):
                    rec["wind_dir_deg"] = float(wdir)
                if isinstance(wspd, (int, float)):
                    rec["wind_speed_ms"] = float(wspd)
                if isinstance(rain, (int, float)):
                    rec["rain_hour_mm"] = float(rain)
                records.append(rec)
    return records

def generate_school_lesson01(records: List[Dict[str, str | float]]) -> str:
    """基于学校数据生成第1课 CSV（时间、气温/°C）。

    输出列：`time,temp_c`。
    """
    rows: List[List[str]] = []
    for rec in records:
        t = rec.get("time")
        temp = rec.get("temp_c")
        if t and isinstance(temp, (int, float)):
            rows.append([str(t), f"{float(temp):.1f}"])
    out = os.path.join(ASSETS_DATA_DIR, "lesson-01-sample.csv")
    return write_csv_with_backup(out, ["time", "temp_c"], rows)

def generate_school_lesson04(records: List[Dict[str, str | float]], env_label: str = "校园室外") -> str:
    """基于学校数据生成第4课 CSV（时间、环境类型、气温/°C）。

    输出列：`time,env,temp_c`。环境类型统一标注为 `校园室外`。
    """
    rows: List[List[str]] = []
    for rec in records:
        t = rec.get("time")
        temp = rec.get("temp_c")
        if t and isinstance(temp, (int, float)):
            rows.append([str(t), env_label, f"{float(temp):.1f}"])
    out = os.path.join(ASSETS_DATA_DIR, "lesson-04-sample.csv")
    return write_csv_with_backup(out, ["time", "env", "temp_c"], rows)

def generate_school_lesson05(records: List[Dict[str, str | float]]) -> str:
    """基于学校数据生成第5课 CSV（时间、风向/度、风速/m·s⁻¹）。

    输出列：`time,wind_dir_deg,wind_speed_ms`。
    """
    rows: List[List[str]] = []
    for rec in records:
        t = rec.get("time")
        d = rec.get("wind_dir_deg")
        s = rec.get("wind_speed_ms")
        if t and isinstance(d, (int, float)) and isinstance(s, (int, float)):
            rows.append([str(t), f"{float(d):.1f}", f"{float(s):.2f}"])
    out = os.path.join(ASSETS_DATA_DIR, "lesson-05-sample.csv")
    return write_csv_with_backup(out, ["time", "wind_dir_deg", "wind_speed_ms"], rows)

def generate_school_lesson06(records: List[Dict[str, str | float]]) -> str:
    """基于学校数据生成第6课 CSV（时间、降雨强度/mm·h⁻¹、累计/mm）。

    输出列：`time,rain_mm_per_h,cum_mm`；累计为顺序累加小时雨量。
    """
    rows: List[List[str]] = []
    cum = 0.0
    for rec in records:
        t = rec.get("time")
        r = rec.get("rain_hour_mm")
        if t and isinstance(r, (int, float)):
            val = float(r)
            cum += max(val, 0.0)
            rows.append([str(t), f"{val:.2f}", f"{cum:.2f}"])
    out = os.path.join(ASSETS_DATA_DIR, "lesson-06-sample.csv")
    return write_csv_with_backup(out, ["time", "rain_mm_per_h", "cum_mm"], rows)

def compute_sha256(path: str) -> str:
    """计算指定文件的 SHA256 校验值。

    Args:
        path: 文件路径。

    Returns:
        十六进制字符串形式的 SHA256 值。
    """

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def write_lesson15_metadata(
    dataset_short_name: str,
    doi: str,
    download_date_utc: str,
    sha256: str,
    source_url: str,
    local_path: str,
    derived_csv: str,
    derived_image: str,
) -> str:
    """写出第15课相关数据的元数据 JSON 文件。

    元数据包含数据集短名、DOI、下载日期、SHA256 校验、来源URL、本地路径与派生资产。

    Args:
        dataset_short_name: 数据集短名（如 MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V52）。
        doi: DOI 标识符（如 10.5067/GMSLM-TJ152）。
        download_date_utc: 下载日期（UTC，YYYY-MM-DD）。
        sha256: 原始文件的 SHA256 校验值。
        source_url: 原始数据下载链接（可受保护）。
        local_path: 本地原始文件路径。
        derived_csv: 生成的教学用 CSV 路径。
        derived_image: 生成的教学用图像路径。

    Returns:
        写出的元数据 JSON 文件路径。
    """

    # 从短名推断版本（如 ..._V52 -> 5.2），若失败则为空
    version = None
    if dataset_short_name and dataset_short_name.upper().endswith("_V52"):
        version = "5.2"

    meta = {
        "dataset_short_name": dataset_short_name,
        "doi": doi,
        "dataset_version": version,
        "download_date": download_date_utc,
        "sha256": sha256,
        "source_url": source_url,
        "local_path": local_path,
        "derived_csv": derived_csv,
        "derived_image": derived_image,
    }

    os.makedirs(os.path.dirname(LESSON15_METADATA_JSON), exist_ok=True)
    with open(LESSON15_METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return LESSON15_METADATA_JSON


@dataclass
class AnnualTempRecord:
    """年均温度异常记录。

    Attributes:
        year: 年份（整数）
        temp_anomaly_c: 年度温度异常（°C，相对1951–1980基准）
    """

    year: int
    temp_anomaly_c: float


@dataclass
class AnnualCO2Record:
    """年均 CO₂ 浓度记录。

    Attributes:
        year: 年份（整数）
        co2_ppm: 年均 CO₂ 浓度（ppm）
    """

    year: int
    co2_ppm: float


@dataclass
class AnnualSeaLevelRecord:
    """年均全球海平面高度记录（相对参考均值的异常）。

    Attributes:
        year: 年份（整数）
        sea_level_mm: 年均全球海平面高度异常（mm）

    说明：
        数据来源建议使用 NASA JPL/PO.DAAC 合成的 GMSL（ASCII，V5.x）或
        NASA_SSH_GMSL_INDICATOR 文本文件。原始单位可能为厘米（cm）或毫米（mm），
        本函数统一转换输出为 mm。
    """

    year: int
    sea_level_mm: float


def ensure_dirs() -> None:
    """确保输出目录存在。

    创建 `assets/data` 与 `assets/images` 目录，若不存在则自动创建。
    """

    os.makedirs(ASSETS_DATA_DIR, exist_ok=True)
    os.makedirs(ASSETS_IMAGES_DIR, exist_ok=True)


def parse_gistemp_annual_jd(path: str) -> List[AnnualTempRecord]:
    """解析 NASA GISTEMP 年均（J-D）温度异常。

    该文件的表头为：Year, Jan...Dec, J-D, D-N, DJF, MAM, JJA, SON。
    部分年份可能含有缺失标记"***"，需过滤。

    Args:
        path: GISTEMP CSV 文件路径。

    Returns:
        年均温度异常记录列表。
    """

    records: List[AnnualTempRecord] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = None
        # 跳过前言行，直到遇到包含 Year 与 J-D 的表头
        for row in reader:
            if row and row[0].strip() == "Year" and "J-D" in row:
                header = row
                break

        if header is None:
            raise RuntimeError("未找到表头（Year, ..., J-D），请检查 GISTEMP 文件格式")

        # 找到 J-D 年均列索引
        jd_index = header.index("J-D")

        for row in reader:
            if not row or not row[0].strip():
                continue
            year_str = row[0].strip()
            # 过滤非数值年份（例如注释）
            if not year_str.isdigit():
                continue
            year = int(year_str)
            jd_val = row[jd_index].strip()
            # 缺失值标记为 '***'，过滤
            if jd_val == "***" or jd_val == "":
                continue
            try:
                temp_anomaly = float(jd_val)
            except ValueError:
                # 例如 '.91' 前有符号，仍尝试转换
                temp_anomaly = float(jd_val.replace(" ", ""))
            records.append(AnnualTempRecord(year=year, temp_anomaly_c=temp_anomaly))
    return records


def parse_noaa_co2_annual_mean(path: str) -> List[AnnualCO2Record]:
    """解析 NOAA Mauna Loa 月均 CO₂ 并计算年均。

    输入为 NOAA GML 提供的月度 CSV。文件包含以 `#` 开头的注释行。
    有效字段表头：`year,month,decimal date,average,deseasonalized,ndays,sdev,unc`。

    年均计算方法：对同一年份的 `average` 取算术平均；若某月缺失（负或缺失），按 NOAA 已处理值参与平均。

    Args:
        path: NOAA 月度 CSV 文件路径。

    Returns:
        年均 CO₂ 浓度记录列表。
    """

    # 跳过注释行，逐行解析
    yearly: Dict[int, List[float]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5 or not parts[0].isdigit():
                continue
            year = int(parts[0])
            try:
                avg = float(parts[3])
            except ValueError:
                # 遇到非数值，跳过该月
                continue
            yearly.setdefault(year, []).append(avg)

    records: List[AnnualCO2Record] = []
    for year, values in sorted(yearly.items()):
        if not values:
            continue
        co2_mean = sum(values) / len(values)
        records.append(AnnualCO2Record(year=year, co2_ppm=co2_mean))
    return records


def moving_average(series: List[Tuple[int, float]], window: int = 5) -> List[Tuple[int, float]]:
    """计算简单滑动均值。

    Args:
        series: 序列 `(year, value)` 列表。
        window: 窗口大小，默认 5。

    Returns:
        与输入长度一致的 `(year, ma_value)` 列表；前 `window-1` 项按已有前缀平均。
    """

    acc: List[Tuple[int, float]] = []
    values: List[float] = []
    for i, (year, val) in enumerate(series):
        values.append(val)
        # 取最近 window 项
        w = values[max(0, i - window + 1) : i + 1]
        acc.append((year, sum(w) / len(w)))
    return acc


def write_csv(path: str, header: List[str], rows: List[List[object]]) -> None:
    """写入 CSV 文件，确保父目录存在。

    Args:
        path: 输出文件路径。
        header: 表头列名列表。
        rows: 数据行列表。
    """

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def generate_lesson12_csv(temp_records: List[AnnualTempRecord]) -> str:
    """生成第12课教学用 CSV：年份、气温/°C、滑动均值。

    Args:
        temp_records: 年均温度异常记录列表。

    Returns:
        输出文件路径。
    """

    series = [(r.year, r.temp_anomaly_c) for r in temp_records]
    ma_series = moving_average(series, window=5)

    rows = []
    for (year, val), (_, ma) in zip(series, ma_series):
        rows.append([year, round(val, 3), round(ma, 3)])

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-12-sample.csv")
    write_csv(out_path, ["年份", "气温/°C", "滑动均值"], rows)
    return out_path


def generate_lesson21_csv(temp_records: List[AnnualTempRecord], co2_records: List[AnnualCO2Record]) -> str:
    """生成第21课教学用 CSV：年份、CO₂/ppm、温度异常/°C。

    Args:
        temp_records: 年均温度异常记录列表。
        co2_records: 年均 CO₂ 浓度记录列表。

    Returns:
        输出文件路径。
    """

    temp_map = {r.year: r.temp_anomaly_c for r in temp_records}
    rows = []
    for r in co2_records:
        if r.year in temp_map:
            rows.append([r.year, round(r.co2_ppm, 3), round(temp_map[r.year], 3)])

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-21-sample.csv")
    write_csv(out_path, ["年份", "CO₂/ppm", "温度异常/°C"], rows)
    return out_path


def configure_matplotlib_for_mac_chinese() -> None:
    """在 macOS 上配置中文字体显示规范。

    使用 Heiti TC 作为默认中文字体，并设置 `axes.unicode_minus` 为 False。
    """

    plt.rcParams["font.family"] = "Heiti TC"
    plt.rcParams["axes.unicode_minus"] = False


def plot_lesson15_temp_anomaly(temp_records: List[AnnualTempRecord]) -> str:
    """生成第15课示例图：全球温度异常折线图。

    Args:
        temp_records: 年均温度异常记录列表。

    Returns:
        输出图片路径。
    """

    configure_matplotlib_for_mac_chinese()
    years = [r.year for r in temp_records]
    vals = [r.temp_anomaly_c for r in temp_records]

    plt.figure(figsize=(10, 5), dpi=160)
    plt.plot(years, vals, color="#d62728", linewidth=2, label="温度异常（°C）")
    plt.title("全球温度异常（年均，GISTEMP）")
    plt.xlabel("年份")
    plt.ylabel("温度异常（°C）")
    plt.grid(True, alpha=0.3)
    plt.legend()
    out_path = os.path.join(ASSETS_IMAGES_DIR, "lesson-15-evidence.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def parse_jpl_gmsl_ascii(file_path: str) -> List[AnnualSeaLevelRecord]:
    """解析 NASA JPL/NOAA 全球海平面高度（GMSL）ASCII 文本，汇总为年度平均。

    支持的数据文件类型：
    - MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V5.x（PO.DAAC，单位为 mm，带注释行 HDR）
    - NASA_SSH_GMSL_INDICATOR.txt（单位为 cm，包含 60 天平滑列）

    解析策略（鲁棒）：
    - 跳过注释与头部行：以 "#"、"HDR" 开头或包含 "Header_End" 的行
    - 优先空白分隔；兼容逗号分隔
    - V5.x 行格式：`[type, cycle, year_frac, ... , col6..col13]`
      - 年份取 `int(float(parts[2]))`
      - 海平面值优先取列11（`parts[10]`，GIA applied smoothed，mm），若解析失败回退列8（`parts[7]`）
      - 过滤缺失标记 `99900.000`
    - 指标文件行格式：首列为日期（YYYY-MM-DD / YYYY/MM/DD），取后续首个数值为海平面值
    - 单位自适应：若绝大多数值绝对值 < 20，视为 cm，乘以 10 转换为 mm
    - 按年份聚合平均，输出年度 mm 异常

    Args:
        file_path: 输入 ASCII 文本文件路径。

    Returns:
        年均海平面记录列表（mm）。
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到海平面数据文件: {file_path}")

    # 暂存每日/每周期数值
    per_year_values: Dict[int, List[float]] = {}
    candidate_values: List[float] = []

    def is_float(s: str) -> bool:
        try:
            float(s)
            return True
        except ValueError:
            return False

    def looks_like_date(token: str) -> bool:
        token = token.strip()
        return (
            len(token) >= 10
            and token[:4].isdigit()
            and (token[4] == '-' or token[4] == '/')
        )

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if (
                not line
                or line.startswith("#")
                or line.upper().startswith("HDR")
                or "Header_End" in line
            ):
                continue

            # 逗号或空白分隔
            parts = (
                [p for p in line.replace("\t", " ").split(",") if p.strip()]
                if "," in line
                else [p for p in line.split() if p.strip()]
            )
            if not parts:
                continue

            year: int | None = None
            val: float | None = None

            # 识别 V5.x 行（首列/次列为数字且第三列为年小数）
            if len(parts) >= 11 and parts[0].lstrip("-+").isdigit() and parts[1].lstrip("-+").isdigit() and is_float(parts[2]):
                try:
                    year = int(float(parts[2]))
                except ValueError:
                    year = None
                # 优先列11（GIA applied smoothed），回退列8（GIA not applied smoothed）
                chosen_idx = 10
                if not is_float(parts[chosen_idx]) and len(parts) >= 8 and is_float(parts[7]):
                    chosen_idx = 7
                if is_float(parts[chosen_idx]):
                    val_candidate = float(parts[chosen_idx])
                    # 过滤缺失值标记
                    if abs(val_candidate) < 99900.0:
                        val = val_candidate

            # 识别指标文件行（首列看起来像日期）
            elif looks_like_date(parts[0]):
                year = int(parts[0][:4])
                # 取日期后的首个数值作为海平面值
                for p in parts[1:]:
                    if is_float(p):
                        val = float(p)
                        break

            # 若上述均未匹配，但首列形似年份（YYYY）
            elif len(parts[0]) >= 4 and parts[0][:4].isdigit():
                year = int(parts[0][:4])
                for p in parts[1:]:
                    if is_float(p):
                        val = float(p)
                        break

            # 收集并聚合
            if year is None or val is None:
                continue
            candidate_values.append(abs(val))
            per_year_values.setdefault(year, []).append(val)

    # 单位自适应：若大多数值绝对值 < 20，则视为 cm -> 转 mm
    to_mm_factor = 1.0
    if candidate_values:
        small_fraction = sum(1 for v in candidate_values if v < 20.0) / len(candidate_values)
        if small_fraction > 0.8:
            to_mm_factor = 10.0

    records: List[AnnualSeaLevelRecord] = []
    for year, vals in sorted(per_year_values.items()):
        if not vals:
            continue
        avg_mm = sum(vals) / len(vals) * to_mm_factor
        records.append(AnnualSeaLevelRecord(year=year, sea_level_mm=float(avg_mm)))

    return records


def generate_lesson15_csv(temp_records: List[AnnualTempRecord], sea_records: List[AnnualSeaLevelRecord]) -> str:
    """生成第15课教学用 CSV：年份、温度异常/°C、海平面/mm。

    合并策略：
    - 以年份为键，将 GISTEMP 年度异常与 GMSL 年度平均按年份合并。
    - 输出列为 [年份, 温度异常/°C, 海平面/mm]。

    Args:
        temp_records: 年均温度异常记录列表。
        sea_records: 年均海平面高度记录列表（mm）。

    Returns:
        输出文件路径。
    """

    temp_map = {r.year: r.temp_anomaly_c for r in temp_records}
    rows: List[List[float]] = []
    for r in sea_records:
        if r.year in temp_map:
            rows.append([r.year, round(temp_map[r.year], 3), round(r.sea_level_mm, 2)])

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-15-sample.csv")
    write_csv(out_path, ["年份", "温度异常/°C", "海平面/mm"], rows)
    return out_path


def plot_lesson21_co2_temp(temp_records: List[AnnualTempRecord], co2_records: List[AnnualCO2Record]) -> str:
    """生成第21课示例图：CO₂ 与温度异常双轴折线图。

    此图通过双轴展示全球年均温度异常与年均 CO₂ 浓度的时间序列关系。
    为避免中文字体 Heiti TC 缺少下标字符“₂”的显示问题，图中的
    “CO₂”文本均使用 LaTeX 样式的 mathtext 语法渲染为 ``$\mathrm{CO_2}$``。
    这不依赖外部 LaTeX 环境，直接使用 Matplotlib 内置的 mathtext 引擎。

    Args:
        temp_records: 年均温度异常记录列表。
        co2_records: 年均 CO₂ 浓度记录列表。

    Returns:
        输出图片路径。
    """

    configure_matplotlib_for_mac_chinese()
    # 对齐年份范围
    temp_map = {r.year: r.temp_anomaly_c for r in temp_records}
    co2_map = {r.year: r.co2_ppm for r in co2_records}
    common_years = sorted(set(temp_map.keys()) & set(co2_map.keys()))
    if not common_years:
        raise RuntimeError("CO₂ 与温度异常无交集年份，无法绘图")

    years = common_years
    temp_vals = [temp_map[y] for y in years]
    co2_vals = [co2_map[y] for y in years]

    plt.figure(figsize=(10, 5), dpi=160)
    ax1 = plt.gca()
    ax2 = ax1.twinx()

    ax1.plot(years, temp_vals, color="#d62728", linewidth=2, label="温度异常（°C）")
    ax2.plot(years, co2_vals, color="#1f77b4", linewidth=2, label=r"$\mathrm{CO_2}$（ppm）")

    ax1.set_xlabel("年份")
    ax1.set_ylabel("温度异常（°C）", color="#d62728")
    ax2.set_ylabel(r"$\mathrm{CO_2}$（ppm）", color="#1f77b4")
    plt.title(r"$\mathrm{CO_2}$ 与全球温度异常（年均）")
    ax1.grid(True, alpha=0.3)

    # 合并图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    plt.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    out_path = os.path.join(ASSETS_IMAGES_DIR, "lesson-21-co2-temp.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def main() -> None:
    """主函数：执行数据解析、加工与输出图像生成。

    执行步骤：
    1. 读取并解析 GISTEMP 与 NOAA CO₂ 数据（必需）
    2. 如存在海平面数据文件，解析并生成第15课 CSV 到 `assets/data`
    3. 生成第12课与第21课 CSV 到 `assets/data`
    4. 生成第15课与第21课教学示例图到 `assets/images`
    """

    ensure_dirs()

    # 写原始数据元数据（如文件存在）。
    try:
        raw_meta_path = write_raw_sources_metadata()
    except Exception as e:
        raw_meta_path = None
        print(f"警告：原始数据元数据写入失败 -> {e}")

    # 为每个原始文件写旁注元数据（下载即写元数据的语义表现）。
    try:
        sidecar_paths = write_raw_sidecar_metadata()
    except Exception as e:
        sidecar_paths = []
        print(f"警告：原始数据旁注元数据写入失败 -> {e}")

    if not os.path.exists(GISTEMP_CSV):
        raise FileNotFoundError(f"未找到 GISTEMP 数据文件: {GISTEMP_CSV}")
    if not os.path.exists(NOAA_CO2_MONTHLY_CSV):
        raise FileNotFoundError(f"未找到 NOAA CO₂ 月度数据文件: {NOAA_CO2_MONTHLY_CSV}")

    temp_records = parse_gistemp_annual_jd(GISTEMP_CSV)
    co2_records = parse_noaa_co2_annual_mean(NOAA_CO2_MONTHLY_CSV)

    # 可选：海平面数据（NASA JPL/NOAA）
    lesson15_csv_path: str | None = None
    if os.path.exists(SEA_LEVEL_ASCII):
        sea_records = parse_jpl_gmsl_ascii(SEA_LEVEL_ASCII)
        lesson15_csv_path = generate_lesson15_csv(temp_records, sea_records)
    else:
        print(f"提示：未找到海平面数据文件，跳过第15课 CSV 生成 -> {SEA_LEVEL_ASCII}")

    path12 = generate_lesson12_csv(temp_records)
    path21 = generate_lesson21_csv(temp_records, co2_records)
    img15 = plot_lesson15_temp_anomaly(temp_records)
    img21 = plot_lesson21_co2_temp(temp_records, co2_records)

    # 写出第15课的元数据（如海平面数据存在）
    if lesson15_csv_path and os.path.exists(SEA_LEVEL_ASCII):
        sha256 = compute_sha256(SEA_LEVEL_ASCII)
        dataset_short_name = "MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V52"
        doi = "10.5067/GMSLM-TJ152"
        download_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        source_url = (
            "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus/Protected/"
            "MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V52/merged_global_sea_level_v5.2.txt"
        )
        write_lesson15_metadata(
            dataset_short_name=dataset_short_name,
            doi=doi,
            download_date_utc=download_date_utc,
            sha256=sha256,
            source_url=source_url,
            local_path=SEA_LEVEL_ASCII,
            derived_csv=lesson15_csv_path,
            derived_image=img15,
        )

    # 基于“曹杨中学”数据生成第1/4/5/6课配套CSV
    if os.path.isdir(SCHOOL_DIR):
        school_records = read_school_xls_rows(SCHOOL_DIR)
        p01 = generate_school_lesson01(school_records)
        p04 = generate_school_lesson04(school_records)
        p05 = generate_school_lesson05(school_records)
        p06 = generate_school_lesson06(school_records)
    else:
        p01 = p04 = p05 = p06 = None

    # 第2/3课：树轮 + 冰芯；石笋 + 岩芯
    path02 = None
    path03 = None
    if os.path.exists(ITRDB_RWL_CANA426) and os.path.exists(NGRIP_D18O_20YR):
        try:
            tree_records = parse_itrdb_rwl_template(ITRDB_RWL_CANA426)
            ice_records = parse_vinther_ngrip_20yr(NGRIP_D18O_20YR)
            path02 = generate_lesson02_csv(tree_records, ice_records)
            write_lesson02_metadata(path02)
        except Exception as e:
            print(f"警告：第2课数据处理失败 -> {e}")
    else:
        print(f"提示：第2课数据不存在或不全，跳过 -> {ITRDB_RWL_CANA426}, {NGRIP_D18O_20YR}")

    if os.path.exists(SPELEO_XL16) and os.path.exists(WALKER_GS):
        try:
            speleo_records = parse_speleothem_xl16_growth(SPELEO_XL16)
            core_records = parse_walker_grainsize(WALKER_GS)
            path03 = generate_lesson03_csv(speleo_records, core_records)
            write_lesson03_metadata(path03)
        except Exception as e:
            print(f"警告：第3课数据处理失败 -> {e}")
    else:
        print(f"提示：第3课数据不存在或不全，跳过 -> {SPELEO_XL16}, {WALKER_GS}")

    print("生成完成：")
    print(f"- 第12课 CSV: {path12}")
    print(f"- 第21课 CSV: {path21}")
    if lesson15_csv_path:
        print(f"- 第15课 CSV: {lesson15_csv_path}")
    else:
        print("- 第15课 CSV: 跳过（待提供 NASA/NOAA 海平面数据）")
    print(f"- 第15课 图像: {img15}")
    print(f"- 第21课 图像: {img21}")
    if p01:
        print(f"- 第1课 CSV: {p01}")
    if p04:
        print(f"- 第4课 CSV: {p04}")
    if p05:
        print(f"- 第5课 CSV: {p05}")
    if p06:
        print(f"- 第6课 CSV: {p06}")
    if raw_meta_path:
        print(f"- 原始数据元数据: {raw_meta_path}")
    if sidecar_paths:
        print(f"- 原始数据旁注元数据（{len(sidecar_paths)} 件）: 示例 {sidecar_paths[0]}")
    if path02:
        print(f"- 第2课 CSV: {path02}")
    else:
        print("- 第2课 CSV: 跳过（待提供 ITRDB/NGRIP 数据）")
    if path03:
        print(f"- 第3课 CSV: {path03}")
    else:
        print("- 第3课 CSV: 跳过（待提供 石笋/湖泊岩芯数据）")


if __name__ == "__main__":
    main()
def parse_jpl_gmsl_ascii(file_path: str) -> List[AnnualSeaLevelRecord]:
    """解析 NASA JPL/NOAA 全球海平面高度（GMSL）ASCII 文本，汇总为年度平均。

    支持的数据文件类型：
    - MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V5.x（PO.DAAC，单位通常为 mm，带注释行）
    - NASA_SSH_GMSL_INDICATOR.txt（单位为 cm，包含 60 天平滑列）

    解析策略：
    - 跳过注释行（以 "#" 开头）与空行
    - 对每行进行分隔（优先逗号，其次空白）
    - 尝试从首列提取日期（优先识别 YYYY-MM-DD；若仅有年度，直接使用）
    - 从数值列选择第一个海平面值（单位自适应：若绝对值普遍 < 20，视为 cm，乘以 10 转换为 mm）
    - 按年份聚合平均，输出年度 mm 异常

    Args:
        file_path: 输入 ASCII 文本文件路径。

    Returns:
        年均海平面记录列表（mm）。
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到海平面数据文件: {file_path}")

    # 暂存每日/每周期数值
    per_year_values: Dict[int, List[float]] = {}
    candidate_values: List[float] = []

    def parse_year(token: str) -> int | None:
        # 尝试多格式：YYYY-MM-DD / YYYY/MM/DD / YYYY
        token = token.strip()
        if len(token) >= 4 and token[:4].isdigit():
            try:
                return int(token[:4])
            except ValueError:
                return None
        return None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # 逗号或空白分隔
            parts = [p for p in line.replace("\t", " ").split(",") if p.strip()] if "," in line else [p for p in line.split() if p.strip()]
            if not parts:
                continue
            year = parse_year(parts[0])
            # 收集数值列（跳过非数值）
            values: List[float] = []
            for p in parts[1:]:
                try:
                    values.append(float(p))
                except ValueError:
                    # 可能是日期或文本，忽略
                    continue
            if not values:
                continue
            # 选择第一个数值作为海平面异常
            val = values[0]
            candidate_values.append(abs(val))
            if year is not None:
                per_year_values.setdefault(year, []).append(val)

    # 单位自适应：若大多数值绝对值 < 20，则视为 cm -> 转 mm
    to_mm_factor = 1.0
    if candidate_values:
        small_fraction = sum(1 for v in candidate_values if v < 20.0) / len(candidate_values)
        if small_fraction > 0.8:
            to_mm_factor = 10.0

    records: List[AnnualSeaLevelRecord] = []
    for year, vals in sorted(per_year_values.items()):
        if not vals:
            continue
        avg_mm = sum(vals) / len(vals) * to_mm_factor
        records.append(AnnualSeaLevelRecord(year=year, sea_level_mm=float(avg_mm)))

    return records


def generate_lesson15_csv(temp_records: List[AnnualTempRecord], sea_records: List[AnnualSeaLevelRecord]) -> str:
    """生成第15课教学用 CSV：年份、温度异常/°C、海平面/mm。

    合并策略：
    - 以年份为键，将 GISTEMP 年度异常与 GMSL 年度平均按年份合并。
    - 输出列为 [年份, 温度异常/°C, 海平面/mm]。

    Args:
        temp_records: 年均温度异常记录列表。
        sea_records: 年均海平面高度记录列表（mm）。

    Returns:
        输出文件路径。
    """

    temp_map = {r.year: r.temp_anomaly_c for r in temp_records}
    rows: List[List[float]] = []
    for r in sea_records:
        if r.year in temp_map:
            rows.append([r.year, round(temp_map[r.year], 3), round(r.sea_level_mm, 2)])

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-15-sample.csv")
    write_csv(out_path, ["年份", "温度异常/°C", "海平面/mm"], rows)
    return out_path
def parse_jpl_gmsl_ascii(file_path: str) -> List[AnnualSeaLevelRecord]:
    """解析 NASA JPL/NOAA 全球海平面高度（GMSL）ASCII 文本，汇总为年度平均。

    支持的数据文件类型：
    - MERGED_TP_J1_OSTM_OST_GMSL_ASCII_V5.x（PO.DAAC，单位通常为 mm，带注释行）
    - NASA_SSH_GMSL_INDICATOR.txt（单位为 cm，包含 60 天平滑列）

    解析策略：
    - 跳过注释行（以 "#" 开头）与空行
    - 对每行进行分隔（优先逗号，其次空白）
    - 尝试从首列提取日期（优先识别 YYYY-MM-DD；若仅有年度，直接使用）
    - 从数值列选择第一个海平面值（单位自适应：若绝对值普遍 < 20，视为 cm，乘以 10 转换为 mm）
    - 按年份聚合平均，输出年度 mm 异常

    Args:
        file_path: 输入 ASCII 文本文件路径。

    Returns:
        年均海平面记录列表（mm）。
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到海平面数据文件: {file_path}")

    # 暂存每日/每周期数值
    per_year_values: Dict[int, List[float]] = {}
    candidate_values: List[float] = []

    def parse_year(token: str) -> int | None:
        # 尝试多格式：YYYY-MM-DD / YYYY/MM/DD / YYYY
        token = token.strip()
        if len(token) >= 4 and token[:4].isdigit():
            try:
                return int(token[:4])
            except ValueError:
                return None
        return None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # 逗号或空白分隔
            parts = [p for p in line.replace("\t", " ").split(",") if p.strip()] if "," in line else [p for p in line.split() if p.strip()]
            if not parts:
                continue
            year = parse_year(parts[0])
            # 收集数值列（跳过非数值）
            values: List[float] = []
            for p in parts[1:]:
                try:
                    values.append(float(p))
                except ValueError:
                    # 可能是日期或文本，忽略
                    continue
            if not values:
                continue
            # 选择第一个数值作为海平面异常
            val = values[0]
            candidate_values.append(abs(val))
            if year is not None:
                per_year_values.setdefault(year, []).append(val)

    # 单位自适应：若大多数值绝对值 < 20，则视为 cm -> 转 mm
    to_mm_factor = 1.0
    if candidate_values:
        small_fraction = sum(1 for v in candidate_values if v < 20.0) / len(candidate_values)
        if small_fraction > 0.8:
            to_mm_factor = 10.0

    records: List[AnnualSeaLevelRecord] = []
    for year, vals in sorted(per_year_values.items()):
        if not vals:
            continue
        avg_mm = sum(vals) / len(vals) * to_mm_factor
        records.append(AnnualSeaLevelRecord(year=year, sea_level_mm=float(avg_mm)))

    return records


def generate_lesson15_csv(temp_records: List[AnnualTempRecord], sea_records: List[AnnualSeaLevelRecord]) -> str:
    """生成第15课教学用 CSV：年份、温度异常/°C、海平面/mm。

    合并策略：
    - 以年份为键，将 GISTEMP 年度异常与 GMSL 年度平均按年份合并。
    - 输出列为 [年份, 温度异常/°C, 海平面/mm]。

    Args:
        temp_records: 年均温度异常记录列表。
        sea_records: 年均海平面高度记录列表（mm）。

    Returns:
        输出文件路径。
    """

    temp_map = {r.year: r.temp_anomaly_c for r in temp_records}
    rows: List[List[float]] = []
    for r in sea_records:
        if r.year in temp_map:
            rows.append([r.year, round(temp_map[r.year], 3), round(r.sea_level_mm, 2)])

    out_path = os.path.join(ASSETS_DATA_DIR, "lesson-15-sample.csv")
    write_csv(out_path, ["年份", "温度异常/°C", "海平面/mm"], rows)
    return out_path