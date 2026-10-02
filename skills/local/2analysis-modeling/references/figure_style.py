# -*- coding: utf-8 -*-
"""
figure_style.py —— 数学建模国赛 · 通用出图样式库（任何赛题直接复用）
======================================================================
设计定位（对应 3coding-visual 技能 Step 4 与 mathmodel-figure-templates 底座约定）：
  1) 一套 setup() 把「中文字体自检回退 + 中西文混排 + 负号修复 + PDF/SVG 文本化」全部配好；
  2) 统一配色 C / 色带 CMAP_DIV、CMAP_SEQ，正文图表风格一致；
  3) save_fig() 一次导出 PNG(300dpi)+PDF(+SVG)，PDF 矢量供论文直接插入、PNG 供预览/汇报；
  4) 图内不写大标题（标题交给论文 caption），不做流程图/架构图（那是 drawio 的事）。

本机实测：Python 3.13 + matplotlib 3.10，SimHei/SimSun/KaiTi/微软雅黑均在位。
若换机器缺中文字体，会自动按候选顺序回退并给出提示，不会静默出方块。

用法：
    import sys, os
    sys.path.insert(0, r"<本仓库>/math-model-method.md")   # 把本文件所在目录加进路径即可
    import figure_style as fs
    fs.setup(style="cn-serif")        # 或 "cn"（黑体风格）/ "en"（纯英文）
    import matplotlib.pyplot as plt
    import numpy as np
    fig, ax = plt.subplots()
    ax.plot(x, y, color=fs.C[0], label="方案A")
    fs.save_fig(fig, "p2_收敛曲线", folder="figures")       # 自动存 figures/p2_收敛曲线.{png,pdf}

自查：python -X utf8 figure_style.py    —— 会生成 demo 图到 ../reports/figures/ 验证本机字体。
"""
from __future__ import annotations

import os
import sys
import warnings

from pathlib import Path

# 保证中文 print/日志不乱码（GUI 终端不认 utf-8 时也会被此句兜住）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

warnings.filterwarnings("ignore")

import matplotlib as mpl
from matplotlib import font_manager as _fm

# ---------------------------------------------------------------------------
# 配色与图元常量
# ---------------------------------------------------------------------------
# 正文用色板：红/蓝/绿/橙/紫…… 用于折线/柱/散点的类别区分，顺序即 prop_cycle
C = [
    "#2f5597",  # 主蓝
    "#c00000",  # 红
    "#70ad47",  # 绿
    "#ed7d31",  # 橙
    "#7030a0",  # 紫
    "#00b0f0",  # 天蓝
    "#ffc000",  # 黄
    "#7f7f7f",  # 灰
]
CMAP_DIV = "RdBu_r"    # 发散色带：相关矩阵 / 热力差异图
CMAP_SEQ = "Blues"     # 顺序色带：覆盖率 / 数值型热图
MARKERS = ["o", "s", "^", "D", "v", "P", "*", "X"]

_FALLBACK_CJK = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "PingFang SC"]


# ---------------------------------------------------------------------------
# 内部：可用字体检测（按候选顺序返回“真实存在的字体名”列表）
# ---------------------------------------------------------------------------
def _installed() -> set[str]:
    try:
        return {f.name for f in _fm.fontManager.ttflist}
    except Exception:
        return set()


def _resolve(candidates: list[str]) -> list[str]:
    have = _installed()
    kept = [n for n in candidates if n in have]
    if not kept:
        print(f"[figure_style] 警告：候选字体均未安装{candidates}，将使用 matplotlib 默认字体（中文可能显示为方块）")
    return kept or ["DejaVu Sans"]


# ---------------------------------------------------------------------------
# setup()：一键配好出图风格
# ---------------------------------------------------------------------------
def setup(style: str = "cn-serif", font_size: float = 10.5) -> str:
    """
    style：
      "cn-serif"  中文宋体 + 西文 Times New Roman（偏论文规范，中文数字混排首选）
      "cn"        微软雅黑/黑体（无衬线，截图/PPT 醒目）
      "en"        Arial（纯英文报告/复刻 Nature 类模板）
    返回最终启用的西文字体名（调试用）。
    """
    mpl.use("Agg", force=False)          # 无显示环境也能 savefig
    if style == "en":
        primary = ["Arial", "Helvetica", "DejaVu Sans"]
    elif style == "cn":
        # 无衬线：中文优先（微软雅黑/黑体），西文数字跟随，Arial 作兜底
        primary = _FALLBACK_CJK + ["Arial", "DejaVu Sans"]
    else:                                # cn-serif：西文 Times 优先，中文逐字符回退宋体
        primary = ["Times New Roman", "SimSun", "SimHei", "KaiTi",
                   "Noto Serif CJK SC", "DejaVu Serif"]

    primary = _resolve(primary)          # 只保留本机真实存在的字体；顺序即回退优先级
    rcp = {
        # 关键：font.family 必须给“具体字体名列表”才能触发 matplotlib≥3.6 的逐字符回退；
        # 写成 'serif' 这种抽象族名只会取列表第一个字体，中文会缺字形落豆腐块。
        "font.family": primary,
        "font.serif": primary,
        "font.sans-serif": _resolve(_FALLBACK_CJK + ["Arial", "DejaVu Sans"]),
        "font.size": font_size,
        # 负号不显示为方块
        "axes.unicode_minus": False,
        # PDF/SVG 内文字以“文本”而非曲线保存（论文可直接选中/缩放不发虚）
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        # 画布与坐标轴
        "figure.dpi": 100,
        "axes.linewidth": 0.8,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "axes.prop_cycle": mpl.cycler(color=C),
        "figure.autolayout": True,
    }
    mpl.rcParams.update(rcp)
    print(f"[figure_style] style={style} 启用字体族: {primary}")
    return primary[0]


# ---------------------------------------------------------------------------
# 画布尺寸助手：按“论文栏宽厘米”换算英寸
# ---------------------------------------------------------------------------
def figsize_cm(w_cm: float, h_cm: float) -> tuple[float, float]:
    """宽度高度以厘米给（A4 正文栏常用 7.5~15 cm），返回 matplotlib figsize。"""
    return w_cm / 2.54, h_cm / 2.54


def figsize_from_textwidth(width_cm: float, ratio: float = 0.75) -> tuple[float, float]:
    """单栏图：宽=正文宽 width_cm，高按 golden 比例；ratio 可改高宽比。"""
    return figsize_cm(width_cm, width_cm * ratio)


# ---------------------------------------------------------------------------
# save_fig()：一键 PNG + PDF（+SVG）三格式导出
# ---------------------------------------------------------------------------
def save_fig(
    fig,
    stem: str,
    folder: str | os.PathLike | None = None,
    dpi: int = 300,
    formats: tuple[str, ...] = ("png", "pdf"),
    tight: bool = True,
) -> list[Path]:
    """
    保存图片。约定：PDF=论文用（矢量、文本化），PNG=预览/汇报（300dpi），
    SVG=可二次编辑（可选）。图内不写大标题——标题归论文 caption。
    返回已保存文件路径列表。
    """
    if folder is None:
        folder = os.environ.get("FIGOUT", "figures")
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    if tight:
        try:
            fig.set_layout_engine("tight")
        except Exception:
            fig.tight_layout()
    saved: list[Path] = []
    for fmt in formats:
        p = out_dir / f"{stem}.{fmt}"
        kw = {"bbox_inches": "tight", "dpi": dpi} if fmt == "png" else {"bbox_inches": "tight"}
        fig.savefig(p, **kw)
        saved.append(p)
        print(f"    已保存 {p}")
    return saved


# ---------------------------------------------------------------------------
# 随机种子 + 小工具
# ---------------------------------------------------------------------------
def fix_seed(seed: int = 42) -> None:
    """统一随机种子：python 内置 / numpy 全固定，保证图可复现。"""
    import random
    import numpy as np

    random.seed(seed)
    np.random.seed(seed)


def light_axes(ax=None):
    """可选：网格置最淡、隐藏上右框线，适合多图并排时更清爽。"""
    import matplotlib.pyplot as plt

    ax = ax or plt.gca()
    ax.grid(True, alpha=0.18)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return ax


# ---------------------------------------------------------------------------
# 自检：python -X utf8 figure_style.py   → 生成 ../reports/figures/figure_style_demo.*
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt

    setup("cn-serif")
    fix_seed(2025)
    out = Path(__file__).resolve().parent.parent / "reports" / "figures"

    x = np.arange(1, 13)
    y1 = 20 + 4 * np.sin(x / 2.2) + np.random.normal(0, 0.4, x.size)
    y2 = 20 + 4 * np.sin(x / 2.2) + 1.5

    fig, ax = plt.subplots(figsize=figsize_cm(14, 8))
    ax.plot(x, y1, "-o", color=C[0], lw=1.8, ms=4, label="方案A")
    ax.plot(x, y2, "-s", color=C[1], lw=1.6, ms=4, label="方案B")
    ax.fill_between(x, y1 - 0.8, y1 + 0.8, color=C[0], alpha=0.12, label="±σ")
    ax.set_xlabel("孕周 / 周")
    ax.set_ylabel("Y染色体浓度 / %")
    ax.legend(loc="lower right")
    save_fig(fig, "figure_style_demo", folder=out, formats=("png", "pdf"))
    print("[figure_style] 自检完成：字体正常、PNG/PDF 已输出。")
