# Fin4120 零基础固定收益学习站

把香港中文大学（深圳）**Fin4120 Fixed Income Securities** 课程讲义（Instructor: **Prof. Linlin Ye**）重新编排成适合**零基础**学生的静态网站。

> 本站为教育用途的重组讲解与练习，**不是**官方课件副本，也**没有**嵌入原 PDF。请仍以课堂讲义与指定教材（如 Fabozzi）为准。

## 本地打开

1. 下载或克隆本仓库。
2. 用浏览器直接打开根目录的 `index.html` 即可（纯静态，无需安装）。
3. 若个别浏览器限制本地脚本，可在本目录运行：

```bash
python3 -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 用 GitHub Pages 发布（仓库根目录）

本站设计为**仓库根目录即站点根目录**（含 `index.html`），适合 GitHub Pages 的下列设置：

1. 把本文件夹内容推到 GitHub 仓库（可以是仓库根，或 `docs/` 文件夹——若放 `docs/`，在 Pages 设置里选 `docs/`）。
2. 仓库 **Settings → Pages**：
   - Source: Deploy from a branch
   - Branch: `main`（或 `master`）
   - Folder: `/ (root)` —— 若文件在仓库根；若你把整个站点放进 `docs/`，则选 `/docs`
3. 保存后等待一两分钟，访问 `https://<用户名>.github.io/<仓库名>/`

当前推荐：**以本目录为仓库根**，Pages 选 **root**。

## 目录结构

```
fin4120_beginner/
  index.html          # 首页 + 学习路径 + 进度
  glossary.html       # 全站术语表
  modules/m0.html … m8.html
  assets/style.css
  assets/app.js
  README.md
```

## 模块一览

| 模块 | 主题 |
|------|------|
| 0 | 导论与总路线图 |
| 1 | 债券是什么（Fundamentals） |
| 2 | 债券怎么定价（Pricing） |
| 3 | 收益率怎么算（Yield） |
| 4 | 国债与准国债（Treasury / GSE） |
| 5 | 公司债（Corporate Debt） |
| 6 | 国际债券（International） |
| 7 | 收益率曲线（Yield Curve） |
| 8 | 零息曲线构造（Zero Curve） |

学习进度使用浏览器 `localStorage`，仅保存在本机。

## 来源与版权说明

- 概念与结构来自 CUHKSZ Fin4120 lecture slides by Prof. Linlin Ye。
- 文中算例部分来自讲义，部分为帮助初学者理解的**自编简化数字**（页面中已标注）。
- 请勿将本站内容当作投资建议。
