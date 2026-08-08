# LingKuma for Calibre

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md)

**See it? Click it. Learn it!!!**

**哪里不会点哪里**

LingKuma —— *让知识跨越语言的障碍自由传播* —— 是一款围绕阅读设计的翻译与语言学习工具。

你不需要等到“学会”一门语言之后，才能开始阅读这门语言的书籍和其他内容。

遇到不认识的单词，**点一下**。  
遇到看不懂的句子，**点一下**。

LingKuma 帮助你阅读仍在学习中的语言内容，让你在阅读过程中自然地扩大词汇量、熟悉语法和表达方式，并逐渐提高对这门语言的理解能力。

> **先享受阅读，再在阅读中学会一门新的语言。**

## LingKuma 可以做什么？

- 点击单词查看释义
- 翻译并分析完整句子
- 使用 TTS 收听单词发音
- 在阅读过程中积累词汇
- 使用 AI 辅助理解语法和上下文
- 支持多种语言之间的翻译
- 支持亮色和暗色主题
- 在 Calibre 中保留 LingKuma 原有风格的界面

## 效果图

<p align="center">
  <img src="../docs/calibre-ja-zh-light.png" width="48%" alt="Japanese to Chinese in light mode">
  <img src="../docs/calibre-en-ko-dark.png" width="48%" alt="English to Korean in dark mode">
</p>

<p align="center">
  <img src="../docs/calibre-zh-en-light.png" width="48%" alt="Chinese to English in light mode">
  <img src="../docs/calibre-zh-it-dark.png" width="48%" alt="Chinese to Italian in dark mode">
</p>

<p align="center">
  <img src="../docs/calibre-en-ja-light.png" width="65%" alt="English to Japanese in light mode">
</p>

## Calibre 移植版

这是开源项目 LingKuma 的非官方 Calibre 移植版。

Calibre 移植版增加了：

- Calibre / Qt WebEngine 运行环境适配
- 改进 EPUB 和 PDF 阅读中的句子选取
- 支持日文和韩文短句识别
- 适用于 Calibre 的磨砂玻璃效果
- 多语言翻译与 AI 输出支持
- 与 Calibre 阅读环境集成

## 安装

1. 从 **GitHub Releases** 下载 `lingkuma-calibre-1.0.zip`。
2. 打开 **Calibre → 首选项 → 插件**。
3. 选择 **从文件加载插件**。
4. 选择下载的 `lingkuma-calibre-1.0.zip`。
5. 重启 Calibre。

> 不要安装 GitHub 自动生成的 `Source code (zip)`。请使用 Release 附件中的 `lingkuma-calibre-1.0.zip` 插件安装包。

## 其他版本

- [LingKuma for Zotero](https://github.com/white-ink-cell/lingkuma-zotero)
- [LingKuma](https://github.com/lingkuma/LingKuma)

## 支持环境

- Calibre 9.x
- EPUB 和 PDF 阅读
- Windows / macOS / Linux

## 设置

设置界面已经集成到 Calibre 中，包括语言与 AI 设置、词汇管理、TTS 选项、外观设置，以及可选的 WebDAV 备份 / 恢复功能。

## 隐私

LingKuma for Calibre 将本地状态存储在 Calibre 插件数据目录中。翻译、AI、远程 TTS 和 WebDAV 功能可能会向所选择的服务发送完成相应功能所必需的文本或数据。进行普通的单词或句子翻译时，插件不会主动上传完整的电子书或 PDF 文件。

## 上游项目与署名

- 原项目：**LingKuma**
- 上游版本：**LingKuma 1.1.0**
- Calibre 移植版维护与发布：**white-ink-cell**

本仓库提供 LingKuma 的非官方 Calibre 移植版。

该移植版使 LingKuma 能够适配 Calibre 的阅读环境，同时尽可能保留原项目的核心功能、界面、资源和整体设计。针对 Calibre 的修改主要集中在运行环境兼容、句子选取、磨砂玻璃效果以及多语言翻译支持。

更多信息请参阅 `UPSTREAM.md`。

## 许可证

原 LingKuma 项目的作者署名、版权和许可证保持不变。

Calibre 适配器和兼容层使用 `LICENSE-ADAPTER.txt` 中的许可证。原 LingKuma 的许可证保留在 `LICENSE-LINGKUMA.txt` 中，随项目一起提供的第三方许可证和声明记录在 `THIRD-PARTY-NOTICES.txt` 中。
