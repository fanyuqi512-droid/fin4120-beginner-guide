#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build PDF-synced dual-pane site: notes JSON + module shells. Never copies PDFs."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path("/workspace/fin4120_beginner")
EXTRACT = pathlib.Path("/workspace/fin4120_extract")
NOTES = ROOT / "assets" / "notes"
MOD = ROOT / "modules"

# Import explain_for + helpers from existing build_dual.py
spec = importlib.util.spec_from_file_location(
    "build_dual", ROOT / "scripts" / "build_dual.py"
)
bd = importlib.util.module_from_spec(spec)
sys.modules["build_dual"] = bd
spec.loader.exec_module(bd)

MODULES = bd.MODULES
esc = bd.esc
explain_for = bd.explain_for
page_title = bd.page_title
clean_page = bd.clean_page
nav_html = bd.nav_html

EXPECTED_PAGES = {
    "m1": 28,
    "m2": 32,
    "m3": 32,
    "m4": 29,
    "m5": 43,
    "m6": 24,
    "m7": 58,
    "m8": 66,
}

KEYWORDS = {
    "m1": "Fundamentals of Bonds",
    "m2": "Pricing of Bonds",
    "m3": "Yield of Bonds",
    "m4": "Treasury Securities",
    "m5": "Corporate Debt",
    "m6": "International Bond",
    "m7": "Yield Curve & Yield Curve Management",
    "m8": "Deriving The Zero-Coupon Yield Curve",
}


def extract_pages(path: pathlib.Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    pages = [clean_page(p) for p in raw.split("\x0c")]
    # drop trailing empties
    while pages and not pages[-1].strip():
        pages.pop()
    return pages


def is_thin_page(text: str) -> bool:
    body = re.sub(r"\s+", " ", text).strip()
    if len(body) < 60:
        return True
    # mostly a figure/table caption page
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) <= 2 and len(body) < 140:
        return True
    return False


def build_notes_for(mod: dict) -> dict:
    mid = mod["id"]
    pages_raw = extract_pages(EXTRACT / mod["file"])
    expected = EXPECTED_PAGES[mid]
    if len(pages_raw) != expected:
        print(
            f"WARN {mid}: extract pages={len(pages_raw)} expected PDF={expected}",
            file=sys.stderr,
        )
        # trim or pad
        if len(pages_raw) > expected:
            pages_raw = pages_raw[:expected]
        else:
            while len(pages_raw) < expected:
                pages_raw.append("")

    out_pages = []
    last_rich_idx = None
    for i, body in enumerate(pages_raw):
        page_num = i + 1
        title = page_title(body) if body.strip() else f"Slide {page_num}"
        thin = is_thin_page(body)
        expl = explain_for(mid, title, body)
        # mark thin pages: keep explanation but flag
        out_pages.append(
            {
                "page": page_num,
                "title": title,
                "thin": thin,
                "explainHtml": expl,
                "excerpt": body[:4000],
            }
        )
        if not thin and body.strip():
            last_rich_idx = i

    # For thin pages, if explanation is generic short, that's fine —
    # viewer will show nearest section note when thin flagged with weak content.
    return {
        "module": mid,
        "deck": mod["deck"],
        "pageCount": expected,
        "pages": out_pages,
    }


def viewer_shell(mod: dict, idx: int) -> str:
    mid = mod["id"]
    title = mod["title"]
    kw = KEYWORDS.get(mid, mod.get("deck") or "")
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>模块 {mid[1:]} · {esc(title)} · Fin4120 零基础学习站</title>
<link rel="stylesheet" href="../assets/style.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
</head>
<body data-module="{mid}" data-deck-keywords="{esc(kw)}" data-assets-base="../assets">
<header class="site">
  <div class="inner">
    <a class="brand" href="../index.html">Fin4120 零基础固收</a>
    <nav>
      <a href="../index.html">学习路径</a>
      <a href="../glossary.html">术语表</a>
      <a href="../index.html#progress">进度</a>
    </nav>
  </div>
</header>
<div class="wrap wide viewer-wrap">
  <p class="muted"><a href="../index.html">← 返回首页</a></p>
  <h1 class="mod-title">模块 {mid[1:]} · {esc(title)}</h1>
  <div class="source-note">
    <strong>Source:</strong> Fin4120 slides — <em>{esc(mod["deck"])}</em>, Prof. Linlin Ye (CUHKSZ)。
    左侧为<strong>课件原件 PDF 页</strong>（需在本机导入，存 IndexedDB，不会上传）；右侧为按页同步的学习解析。
  </div>
  <div class="dual-legend">
    <span><i class="dot L"></i> 左侧：课件原件（PDF.js）</span>
    <span><i class="dot R"></i> 右侧：本页解析</span>
  </div>

  <div class="pdf-toolbar card">
    <div class="pdf-toolbar-row">
      <button type="button" class="btn" id="pdf-prev" title="上一页">← 上一页</button>
      <span class="page-indicator">第 <strong id="pdf-page-label">—</strong> 页</span>
      <button type="button" class="btn" id="pdf-next" title="下一页">下一页 →</button>
      <span class="toolbar-sep"></span>
      <button type="button" class="btn ghost" id="pdf-zoom-out">−</button>
      <span id="pdf-zoom-label" class="muted">115%</span>
      <button type="button" class="btn ghost" id="pdf-zoom-in">+</button>
      <span class="toolbar-sep"></span>
      <button type="button" class="btn ghost" id="mode-toggle" title="无 PDF 时可用文字摘录">文字摘录</button>
      <button type="button" class="btn accent" data-import-pdfs>导入讲义 PDF</button>
    </div>
    <p class="muted tiny" id="import-live"></p>
  </div>

  <div class="pdf-dual">
    <section class="pane pdf-pane" aria-label="课件原件">
      <div class="pane-label">课件原件</div>
      <div class="pane-body pdf-body">
        <div id="pdf-cta" class="pdf-cta" hidden>
          <p><strong>尚未导入本模块课件 PDF</strong></p>
          <p class="muted">点击上方「导入讲义 PDF」选择文件（可一次多选 8 份）。文件只保存在你浏览器的 IndexedDB，不会上传到 GitHub。</p>
          <p class="muted">期望文件：<em>{esc(kw)}</em>（文件名含 Fundamentals / Pricing 等亦可自动识别）。</p>
          <button type="button" class="btn accent" data-import-pdfs>选择 PDF 文件</button>
          <p class="muted" style="margin-top:.8rem">也可先点工具栏「文字摘录」用文本对照学习。</p>
        </div>
        <div id="pdf-canvas-wrap" class="pdf-canvas-wrap" hidden>
          <canvas id="pdf-canvas"></canvas>
        </div>
        <div id="text-fallback" class="text-fallback" hidden></div>
      </div>
    </section>
    <section class="pane explain" aria-label="解析">
      <div class="pane-label">解析（随页同步）</div>
      <div class="pane-body explain-body" id="page-note">
        <p class="muted">加载解析中…</p>
      </div>
    </section>
  </div>

  <div class="card" style="margin-top:1rem">
    <h2>本机导入状态</h2>
    <div id="import-status"><p class="muted">读取中…</p></div>
    <p><button type="button" class="btn ghost" data-clear-pdfs>清除本机全部 PDF</button></p>
  </div>

  <div class="card checklist">
    <label>
      <input type="checkbox" data-module-check="{mid}">
      <span>我已完成本模块（对照课件原件 + 解析），标记进度</span>
    </label>
  </div>
  {nav_html(idx)}
</div>
<footer class="site">
  <p>课件原件归港中深 <strong>Fin4120 Fixed Income Securities</strong>（Prof. Linlin Ye, CUHKSZ）。本站不托管 PDF；右侧解析为个人学习辅助。</p>
</footer>
<script src="../assets/app.js"></script>
<script src="../assets/idb-slides.js"></script>
<script src="../assets/pdf-viewer.js"></script>
</body>
</html>
'''


def build_m0(idx: int) -> str:
    mod = MODULES[idx]
    body = f'''
<div class="source-note">本模块说明如何导入课件 PDF，以及「左原件 / 右解析」双栏怎么用。PDF 只存你本机浏览器，不会上传。</div>
<div class="dual-legend">
  <span><i class="dot L"></i> 左侧：课件原件 PDF 页（PDF.js 渲染）</span>
  <span><i class="dot R"></i> 右侧：按页同步的零基础解析</span>
</div>

<div class="card">
  <h2>导入全部讲义 PDF</h2>
  <p>一次可选多份（8 份）。按文件名或首页标题自动匹配到 m1–m8。</p>
  <p>
    <button type="button" class="btn accent" data-import-pdfs>导入全部讲义 PDF</button>
    <button type="button" class="btn ghost" data-clear-pdfs>清除本机 PDF</button>
  </p>
  <p class="muted tiny" id="import-live"></p>
  <div id="import-status"><p class="muted">读取中…</p></div>
</div>

<div class="card">
  <h2>怎么用双栏</h2>
  <ol>
    <li>先在本页或首页导入 8 份讲义 PDF（只需一次，换浏览器需重导）。</li>
    <li>打开模块后：左侧翻页/缩放看课件原件；右侧自动切换到该页解析。</li>
    <li>若某页以图/表为主，右侧会提示并展示最近相关页的解析。</li>
    <li>没导入 PDF 时，可用「文字摘录」模式继续学；解析数据已内置。</li>
    <li>桌面端左右并排；手机端先 PDF、后解析堆叠。</li>
  </ol>
</div>

<div class="callout tip">
  <div class="label">学习顺序</div>
  模块 1→3 打地基（工具、定价、收益率）→ 4→6 认识市场产品 → 7→8 曲线与零息构造。不要跳过 2/3 直接啃 8。
</div>

<div class="card">
  <h2>你会反复用到的三个直觉</h2>
  <ul class="clean">
    <li><strong>利率 ↑ → 旧债价格 ↓</strong></li>
    <li><strong>票息率 ≠ 收益率</strong>（除非大致平价）</li>
    <li><strong>多出来的收益，通常买的是某种风险</strong>（久期 / 信用 / 流动性 / 汇率）</li>
  </ul>
</div>

<div class="card">
  <h2>八份讲义对照表</h2>
  <table class="simple">
    <tr><th>模块</th><th>讲义</th><th>约页数</th></tr>
    <tr><td>m1</td><td>Fundamentals of Bonds</td><td>28</td></tr>
    <tr><td>m2</td><td>Pricing of Bonds</td><td>32</td></tr>
    <tr><td>m3</td><td>Yield of Bonds</td><td>32</td></tr>
    <tr><td>m4</td><td>Treasury Securities</td><td>29</td></tr>
    <tr><td>m5</td><td>Corporate Debt</td><td>43</td></tr>
    <tr><td>m6</td><td>International Bond</td><td>24</td></tr>
    <tr><td>m7</td><td>Yield Curve &amp; Management</td><td>58</td></tr>
    <tr><td>m8</td><td>Deriving Zero-Coupon Curve</td><td>66</td></tr>
  </table>
</div>
'''
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>模块 0 · 导论：导入课件与双栏用法 · Fin4120 零基础学习站</title>
<link rel="stylesheet" href="../assets/style.css">
</head>
<body data-module="m0" data-assets-base="../assets">
<header class="site">
  <div class="inner">
    <a class="brand" href="../index.html">Fin4120 零基础固收</a>
    <nav>
      <a href="../index.html">学习路径</a>
      <a href="../glossary.html">术语表</a>
      <a href="../index.html#progress">进度</a>
    </nav>
  </div>
</header>
<div class="wrap wide">
  <p class="muted"><a href="../index.html">← 返回首页</a></p>
  <h1 class="mod-title">模块 0 · 导论：导入课件与双栏用法</h1>
  {body}
  <div class="card checklist">
    <label>
      <input type="checkbox" data-module-check="m0">
      <span>我已完成本模块（了解导入与双栏），标记进度</span>
    </label>
  </div>
  {nav_html(idx)}
</div>
<footer class="site">
  <p>课件原件归港中深 <strong>Fin4120 Fixed Income Securities</strong>（Prof. Linlin Ye, CUHKSZ）。PDF 仅存本机；解析为学习辅助。</p>
</footer>
<script src="../assets/app.js"></script>
<script src="../assets/idb-slides.js"></script>
<script src="../assets/pdf-viewer.js"></script>
</body>
</html>
'''


def write_index():
    cards = []
    for m in MODULES:
        cards.append(
            f'''<a class="mod-card" data-mod-card="{m["id"]}" href="modules/{m["id"]}.html">
  <div class="num">模块 {m["id"][1:]} <span data-done-mark="{m["id"]}"></span></div>
  <h3>{esc(m["title"].split("·")[0].strip())}</h3>
  <p>{esc(m["short"])}</p>
</a>'''
        )
    text = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>学习路径 · Fin4120 零基础学习站</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body data-assets-base="assets">
<header class="site">
  <div class="inner">
    <a class="brand" href="index.html">Fin4120 零基础固收</a>
    <nav>
      <a href="index.html">学习路径</a>
      <a href="glossary.html">术语表</a>
      <a href="index.html#progress">进度</a>
    </nav>
  </div>
</header>

<div class="wrap">
  <section class="hero">
    <div class="badge">CUHKSZ · Fin4120 · 课件原件（本地）+ 解析对照</div>
    <h1>固定收益证券：左课件 · 右解析</h1>
    <p>把叶琳琳老师（Prof. Linlin Ye）Fin4120 八份讲义做成<strong>双栏对照</strong>：左边用 PDF.js 渲染<strong>课件原件页</strong>（你在浏览器本地导入，存 IndexedDB，绝不上传），右边是按页同步的零基础中文解析。</p>
    <p style="opacity:.9">桌面端左右并排；手机端先课件、后解析。无 PDF 时仍可切换「文字摘录」。</p>
  </section>

  <div class="card">
    <h2>导入全部讲义 PDF</h2>
    <p>选择你的 8 份 Fin4120 讲义（可多选）。按文件名/首页标题自动归入 m1–m8。文件<strong>只保存在本机浏览器</strong>，不会进 GitHub、不会上传。</p>
    <p>
      <button type="button" class="btn accent" data-import-pdfs>导入全部讲义 PDF</button>
      <button type="button" class="btn ghost" data-clear-pdfs>清除本机 PDF</button>
    </p>
    <p class="muted tiny" id="import-live"></p>
    <div id="import-status"><p class="muted">读取中…</p></div>
  </div>

  <div class="card">
    <h2 id="progress">我的学习进度</h2>
    <p class="muted" data-progress-text>0 / 9 模块已完成（0%）</p>
    <div class="progress-bar-wrap"><div class="progress-bar" data-progress-bar></div></div>
    <p class="muted">进度存在本机浏览器，换设备不会同步。</p>
  </div>

  <div class="card">
    <h2>怎么读双栏</h2>
    <ul class="clean">
      <li><strong>课件原件</strong>：左侧 PDF 逐页显示老师幻灯片；可用 ← → 键翻页。</li>
      <li><strong>解析</strong>：随当前页切换；图/表页会提示并展示近邻解析。</li>
      <li><strong>隐私</strong>：PDF 永不提交到仓库或服务器，仅 IndexedDB。</li>
    </ul>
  </div>

  <h2>推荐学习路线</h2>
  <div class="road">
    <div class="step"><span class="n">0</span><div><strong>导论</strong> — 导入 PDF 与双栏用法</div></div>
    <div class="step"><span class="n">1</span><div><strong>债券是什么</strong> — Fundamentals</div></div>
    <div class="step"><span class="n">2</span><div><strong>怎么定价</strong> — Pricing</div></div>
    <div class="step"><span class="n">3</span><div><strong>收益率</strong> — Yield</div></div>
    <div class="step"><span class="n">4–6</span><div><strong>市场工具</strong> — Treasury → Corporate → International</div></div>
    <div class="step"><span class="n">7–8</span><div><strong>曲线</strong> — Yield Curve → Zero Curve</div></div>
  </div>

  <div class="grid" style="margin-top:1.4rem">
{"".join(cards)}
  </div>

  <div class="card" style="margin-top:1.6rem">
    <h2>使用说明</h2>
    <ul class="clean">
      <li>每模块：课件 PDF 页 + 页级解析、进度打卡、上一/下一模块。</li>
      <li>术语见 <a href="glossary.html">全站术语表</a>。</li>
      <li>源讲义：Fin4120 lecture slides by Prof. Linlin Ye (CUHKSZ)。原文归授课教师；本站解析为个人学习辅助。</li>
    </ul>
  </div>
</div>

<footer class="site">
  <p>课件原件归港中深 <strong>Fin4120 Fixed Income Securities</strong>（Prof. Linlin Ye, CUHKSZ）。本站不托管 PDF；解析为教育用途对照，非官方教材。</p>
  <p>本地进度与 PDF 保存在浏览器（localStorage / IndexedDB），不会上传。</p>
</footer>
<script src="assets/app.js"></script>
<script src="assets/idb-slides.js"></script>
<script src="assets/pdf-viewer.js"></script>
</body>
</html>
'''
    (ROOT / "index.html").write_text(text, encoding="utf-8")
    print("wrote index.html")


def write_readme():
    text = """# Fin4120 零基础固收学习站（课件原件 + 解析对照）

个人学习辅助站点：把 CUHKSZ Fin4120（Prof. Linlin Ye）八份讲义做成**左课件原件 / 右解析**双栏对照。

- 在线：**https://fanyuqi512-droid.github.io/fin4120-beginner-guide/**
- 模块 m0 导论；m1–m8 对应 Fundamentals → Zero Curve
- **PDF 从不上传、也不进入本仓库**。你在浏览器里选择讲义文件后，内容只写入本机 IndexedDB；换设备或清站点数据需重新导入。
- 未导入 PDF 时，可切换「文字摘录」模式继续学习（解析数据已内置）。

## 使用

1. 打开站点首页或模块 0，点「导入全部讲义 PDF」，多选 8 份课件。
2. 进入各模块：左侧翻页看原件，右侧自动同步解析。
3. 进度打卡保存在 localStorage。

## 本地开发

```bash
python3 scripts/build_pdf_dual.py   # 生成 notes JSON + 模块壳
python3 scripts/build_dual.py       # 旧版「左文字摘录」双栏（可选）
```

用任意静态服务器打开仓库根目录即可。
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")
    print("wrote README.md")


def main():
    NOTES.mkdir(parents=True, exist_ok=True)
    MOD.mkdir(parents=True, exist_ok=True)

    for i, m in enumerate(MODULES):
        mid = m["id"]
        if mid == "m0":
            (MOD / "m0.html").write_text(build_m0(i), encoding="utf-8")
            print("wrote m0")
            continue
        notes = build_notes_for(m)
        (NOTES / f"{mid}.json").write_text(
            json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        rich = sum(1 for p in notes["pages"] if not p.get("thin"))
        print(
            f"notes {mid}: {notes['pageCount']} pages, {rich} rich, "
            f"{notes['pageCount'] - rich} thin/fig"
        )
        (MOD / f"{mid}.html").write_text(viewer_shell(m, i), encoding="utf-8")
        print(f"wrote {mid}.html")

    write_index()
    write_readme()
    print("DONE")


if __name__ == "__main__":
    main()
