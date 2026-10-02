#!/usr/bin/env python3
"""v2.0 学术格式配置中心 —— 字体/字号/页面/标题/段落的唯一权威来源。

postprocess_docx.py 与 verify_output.py 都从这里读配置，禁止在脚本里硬编码格式数值。
字号对照：二号22 / 小二18 / 三号16 / 小三15 / 四号14 / 小四12 / 五号10.5 / 小五9（pt）。
"""

from __future__ import annotations

import copy

# 常用字体（避免拼写漂移）
FONT_SONG = "宋体"
FONT_HEI = "黑体"
FONT_LATIN = "Times New Roman"

STYLE_NAMES = ("academic_paper", "course_report", "competition_report")

_BASE = {
    # 一、页面设置：A4，上 2.5 / 下 2.5 / 左 3.0 / 右 2.5 cm
    "page": {
        "width_cm": 21.0,
        "height_cm": 29.7,
        "margin_top_cm": 2.5,
        "margin_bottom_cm": 2.5,
        "margin_left_cm": 3.0,
        "margin_right_cm": 2.5,
    },
    # 二、字体规范：中文宋体小四、西文 Times New Roman；标题黑体
    "fonts": {"body_eastasia": FONT_SONG, "heading_eastasia": FONT_HEI, "latin": FONT_LATIN},
    # 三、正文格式：小四 12pt、首行缩进 2 字符、1.5 倍行距、段前 0、段后 6pt
    "body": {
        "size_pt": 12.0,
        "line_spacing": 1.5,
        "first_line_indent_chars": 2,
        "space_before_pt": 0.0,
        "space_after_pt": 6.0,
    },
    # 四、标题层级：黑体加粗左对齐；三号/四号/小四
    "heading1": {"size_pt": 16.0, "bold": True, "space_before_pt": 17.0, "space_after_pt": 16.5},
    "heading2": {"size_pt": 14.0, "bold": True, "space_before_pt": 13.0, "space_after_pt": 13.0},
    "heading3": {"size_pt": 12.0, "bold": True, "space_before_pt": 13.0, "space_after_pt": 6.0},
    # 文档主标题（Title 样式）：黑体小二居中
    "title": {"size_pt": 18.0, "bold": True},
    # 六、目录：标题黑体三号，正文宋体小四
    "toc": {"title_size_pt": 16.0, "body_size_pt": 12.0, "levels": "1-3"},
    # 七/八、题注：五号宋体居中（图下方/表上方，由 pandoc 约定与 postprocess 保证）
    "caption": {"size_pt": 10.5},
    # 九、参考文献：五号宋体，[1] 编号，悬挂缩进
    "reference": {"size_pt": 10.5, "hanging_indent_pt": 21.0, "space_after_pt": 3.0, "line_spacing": 1.25},
    # 表格：单元格文字五号，单倍行距
    "table": {"cell_size_pt": 10.5},
}

STYLE_CONFIG: dict[str, dict] = {
    "academic_paper": {
        "label": "科研论文/调研报告格式",
        "header_text": "天津大学本科课程/科研报告",
        "footer_page_number": True,
        **copy.deepcopy(_BASE),
    },
    "course_report": {
        "label": "课程报告格式",
        "header_text": "天津大学本科课程报告",
        "footer_page_number": True,
        **copy.deepcopy(_BASE),
    },
    "competition_report": {
        "label": "竞赛申报书格式",
        "header_text": "天津大学竞赛申报书",
        "footer_page_number": True,
        **copy.deepcopy(_BASE),
    },
}


def get_style(name: str) -> dict:
    """按名取样式配置的深拷贝；未知名称给出可用列表，避免静默回落。"""
    if name not in STYLE_CONFIG:
        raise KeyError(f"未知样式 '{name}'，可用：{list(STYLE_CONFIG)}")
    return copy.deepcopy(STYLE_CONFIG[name])


def resolve_style_args(style: str, heading_font: str | None, body_font: str | None,
                       latin_font: str | None) -> dict:
    """CLI 显式字体参数覆盖配置（保持 v1 的 --heading-font 等参数兼容）。"""
    cfg = get_style(style)
    if heading_font:
        cfg["fonts"]["heading_eastasia"] = heading_font
    if body_font:
        cfg["fonts"]["body_eastasia"] = body_font
    if latin_font:
        cfg["fonts"]["latin"] = latin_font
    return cfg
