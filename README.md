# Fin4120 零基础固收学习站（课件原件 + 解析对照）

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
