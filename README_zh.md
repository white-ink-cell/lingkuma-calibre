# LingKuma for Calibre

[English](README.md) | **简体中文** | [日本語](README_ja.md) | [한국어](README_ko.md)

这是基于开源项目 **LingKuma 1.1.0** 制作的非官方 Calibre 桌面移植版，让 LingKuma 的高亮、查词、翻译 / AI、整句分析、词库、TTS 和主题功能可以在 Calibre 阅读环境中使用。

> **Calibre 移植版发布 / 维护：[`white-ink-cell`](https://github.com/white-ink-cell)**  
> 本仓库不是 LingKuma 官方 Calibre 版本。LingKuma 原项目的作者、版权和许可证保持不变；`white-ink-cell` 仅表示本 Calibre 移植版的发布与维护者。

## 效果展示

<p align="center">
  <img src="docs/calibre-ja-zh-light.png" width="48%" alt="Japanese to Chinese in light mode">
  <img src="docs/calibre-en-ko-dark.png" width="48%" alt="English to Korean in dark mode">
</p>
<p align="center">
  <img src="docs/calibre-zh-en-light.png" width="48%" alt="Chinese to English in light mode">
  <img src="docs/calibre-zh-it-dark.png" width="48%" alt="Chinese to Italian in dark mode">
</p>
<p align="center">
  <img src="docs/calibre-en-ja-light.png" width="65%" alt="English to Japanese in light mode">
</p>

## 主要改动

本移植版主要进行了四项适配。

### 1. Calibre 运行环境适配

在 LingKuma 外部增加 Calibre 兼容层，为原本依赖浏览器扩展环境的功能提供 Calibre / Qt WebEngine 所需的运行接口。

尽量保持 LingKuma 原始功能和代码结构不变。

### 2. 句子选取优化

增加适用于 Calibre 阅读环境的句子边界判断和文本重建规则，改善 EPUB、PDF、括号、缩写和特殊标点等情况下的完整句子选取。

**1.0 新增：** 对日文和韩文，有意义的少于 5 个字符的短句或短语，只要包含不止一个词汇单位，也可以打开 Word Explosion 整句面板；单个词仍不会被误判成句子。

### 3. 磨砂玻璃效果适配

原版部分玻璃效果依赖浏览器环境中的 Web 组件和渲染能力，在 Calibre 的 Qt WebEngine 中无法完全正常显示。

移植版保留原来的界面和主题逻辑，并提供适用于 Calibre 的磨砂玻璃兼容效果。

### 4. 多语言翻译适配

原版部分 AI Prompt 和语言处理路径默认以中文为固定目标语言。

移植版补充了源语言识别和目标语言适配，使翻译、AI 解释、TTS 语言元数据及相关语言显示能够按照用户选择的语言工作。

## 安装

1. 打开 **Calibre → 首选项 → 插件**。
2. 如果已经安装旧版 LingKuma for Calibre，请先删除旧版并完全退出 Calibre。
3. 重新打开 Calibre，选择 **从文件加载插件**。
4. 安装 GitHub Releases 中的 `lingkuma-calibre-1.0.zip`。
5. 重启 Calibre。

> 不要把 GitHub 自动生成的 Source code ZIP 当作 Calibre 插件安装包。

## 翻译设置

进入：

`LingKuma → 完整设置 → AI / API 配置`

可使用：

- Google Web Translate（免 Key，实验性）
- Microsoft Translator
- Google Cloud Translation
- LingKuma AI

## 支持格式与环境

可直接打开：

- EPUB
- HTMLZ
- TXT
- HTML / XHTML

其他格式可以通过 Calibre 转换为 EPUB。PDF 的实际效果取决于文本层和原始排版。

运行环境：

- Calibre 7.0+
- Windows / macOS / Linux
- 主要在 Calibre 9.x 上测试

## 数据与隐私

设置、词库、例句和阅读进度默认保存在 Calibre 本地配置目录中。

使用翻译或 AI 服务时，只会向用户选择的服务发送完成请求所需的单词、句子或上下文。插件不会主动上传整本电子书、Calibre 凭据或书库元数据。

API 密钥存储在本地插件状态文件中。WebDAV 同步仅在用户明确请求时执行。

## 上游项目与署名

- 原项目：**LingKuma**
- 上游版本：**LingKuma 1.1.0**
- Calibre 移植版维护 / 发布：**white-ink-cell**

LingKuma 原项目的作者、版权、许可证、核心 UI 和随项目分发的上游资源均继续归属于原项目。

详细说明见 [`UPSTREAM_zh.md`](UPSTREAM_zh.md)。

## 许可证

LingKuma 原项目的作者、版权和许可证保持不变。

Calibre 适配 / 兼容层见 `LICENSE-ADAPTER.txt`；LingKuma 原许可证保存在 `LICENSE-LINGKUMA.txt`；第三方资源的许可与声明见 `THIRD-PARTY-NOTICES.txt` 和 `licenses/`。
