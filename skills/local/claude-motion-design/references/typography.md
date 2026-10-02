# typography.md — 字体系统

## 字族

| 用途 | 字体 | 备注 |
|---|---|---|
| 中文衬线 | **Noto Serif SC**（400/500/600/700） | 经 `@remotion/google-fonts` unicode-range 分块按需加载，首渲需网络 |
| 西文/年份衬线 | **Source Serif 4** | 参考片 Copernicus 的免费最优近似 |
| 英文小字/坐标 | **IBM Plex Mono** | letter-spacing 0.3–0.5em 作 kicker |

栈序：中文场景 `serifCjk = "Noto Serif SC", "Source Serif 4", serif`；纯西文/数字用 `serif`。

## 尺寸比例（1080p 基准，theme.ts 为准）

| 层级 | 字号 | 字重 | 字距 | 画面位置 |
|---|---|---|---|---|
| 大年份（yearCard/photo year） | 230px | 500 | 0.04–0.05em | top 26–34% |
| 照片段标题 | 92px | 600 | 0.1em | top 45.5%（year 同屏时 47%） |
| 蒙太奇衬线行 | 78–84px | 500–600 | 0.06em（中）；0.2em（标语） | centerY 30–45.5% |
| yearCard 名称 | 84px | 600 | 0.3em | top 50% |
| caption 说明 | 30px | 400 | 0.24em | 标题下方 +8.5% |
| endcard 品牌名 | 150px | 600 | 0.18em | top 36% |
| endcard 英文 sub | 34px mono | 400 | 0.5em | top 47% |
| endcard 口号 | 44px | 600 | 0.3em | top 58% |

## 规则

1. **衬线-only**——无衬线体永不出现（参考片全程无 sans）；
2. **ivory `#F0EEE4` 单色字**——强调用字号与字距，不用颜色（印章红仅收束点缀）；
3. **文字阴影双档**：亮底 `0 2px 30px rgba(0,0,0,0.5)` + 暗带兜底；暗底可加 `0 0 60px` 外辉；
4. **字距就是风格**——标语/口号 ≥0.2em（呼吸感），正文标题 0.06–0.1em（庄重）；字距增加须配 `textIndent` 补偿居中；
5. **整词弹入**——6f fade + scale 1.02→1.00（easeOut），退场 4f；**永不逐字符/打字机**；
6. 中文行宽 ≤12 字；超出拆两行进 `text.lines`（引擎自动纵向排布）；
7. 混合大小写优于全大写（参考片为小写文学衬线气质）；年份数字用西文衬线栈。
