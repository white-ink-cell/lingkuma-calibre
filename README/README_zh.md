# LingKuma for Calibre

[English](../README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md)

**See it. Click it. Learn it.**<br>
**哪里不会点哪里**

[LingKuma 原项目](https://github.com/lingkuma/LingKuma) · [LingKuma Wiki](https://docs.lingkuma.org) · [LingKuma 官网](https://lingkuma.org/) · [Zotero 移植版](https://github.com/white-ink-cell/lingkuma-zotero)

LingKuma —— *让知识跨越语言的障碍* —— 是一款围绕阅读设计的翻译与语言学习工具。

你不需要等到“学会”一门语言之后，才能开始阅读这门语言的论文、书籍和文档。

遇到不认识的单词，**点一下**。  
遇到看不懂的句子，**点一下**。

LingKuma 帮助你阅读仍在学习中的语言内容，让你在阅读过程中自然地扩大词汇量、熟悉语法和表达方式，并逐渐提高对这门语言的理解能力。

> **先享受阅读，再在阅读中学会一门新的语言。**

## LingKuma 可以做什么？

- 点击单词查看释义
- 翻译并分析完整句子
- 使用 **Dictionary + Quick Context + AI Detail** 更快、更准确地查词
- 使用字典真人发音收听单词发音，可分别选择美音或英音，并在缺少录音时使用 TTS
- 在阅读过程中积累词汇、释义和个人学习记录
- 使用 AI 辅助理解语法、上下文与复杂句子
- 使用“单词爆炸”快速查看当前句中的多个单词
- 通过自定义按钮一键打开外部词典、搜索引擎或 Wikipedia 等百科网站
- 使用 Bionic Reading、Reading Ruler 和 POS Highlight
- 使用可选 WebDAV 备份 / 恢复学习数据
- 支持亮色和暗色主题

更多 LingKuma 使用说明和平台文档，请查看 [LingKuma Wiki](https://docs.lingkuma.org)。

## 截图

<div align="center">

<p><i>LingKuma in action across different languages and themes.</i></p>

<table>
  <tr>
    <td align="center" width="50%">
      <img src="../docs/calibre-ja-zh-light.png" alt="Japanese to Chinese in light mode" width="95%">
      <br>
      <sub><b>Japanese → Chinese</b></sub><br>
      <sub>Light mode</sub>
    </td>
    <td align="center" width="50%">
      <img src="../docs/calibre-en-ko-dark.png" alt="English to Korean in dark mode" width="95%">
      <br>
      <sub><b>English → Korean</b></sub><br>
      <sub>Dark mode</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../docs/calibre-zh-en-light.png" alt="Chinese to English in light mode" width="95%">
      <br>
      <sub><b>Chinese → English</b></sub><br>
      <sub>Light mode</sub>
    </td>
    <td align="center" width="50%">
      <img src="../docs/calibre-zh-it-dark.png" alt="Chinese to Italian in dark mode" width="95%">
      <br>
      <sub><b>Chinese → Italian</b></sub><br>
      <sub>Dark mode</sub>
    </td>
  </tr>
</table>

<br>

<img src="../docs/calibre-en-ja-light.png" alt="English to Japanese in light mode" width="70%">
<br>
<sub><b>English → Japanese</b></sub><br>
<sub>Light mode</sub>

</div>

## Calibre 移植版

这是开源项目 LingKuma 的非官方 Calibre 移植版。

LingKuma 原版已有单词高亮、句子翻译与分析、词汇学习、语音朗读、Edge TTS 等功能。Calibre 移植版保留这些核心能力，并针对 Calibre 的独立阅读环境进行适配。

Calibre 移植版主要增加或调整了：

- 与 Calibre 的电子书阅读环境集成，在独立的 Qt WebEngine 阅读窗口中使用 LingKuma
- 适配 EPUB 阅读、章节导航、阅读进度及页面外观设置
- 改进 EPUB 阅读中的句子选取和断行修复
- 更完整的断句与句子重建，支持有意义的日文、韩文短句
- 显式英文连字符复合词识别
- Dictionary + Quick Context 加速英文查词
- 适用于 Calibre 的磨砂玻璃效果
- 集成在 Calibre 内的 LingKuma 设置页面，提供语言、词库、TTS、阅读辅助及数据管理等设置
- 修复 Edge TTS 在 Calibre 运行环境中的播放、试听和停止链路

## v1.1.2 本次更新

### 适配 Calibre 阅读环境

本次更新基于 **LingKuma 1.1.1**，继续完善其在 Calibre 中的独立阅读体验。

LingKuma 的阅读、翻译、学习和弹窗界面继续沿用原项目的设计与功能；Calibre 适配层负责电子书解析、Qt WebEngine 阅读窗口、章节导航、阅读进度，以及浏览器扩展运行接口的兼容。

本次进一步补齐了语言设置、词库管理、TTS 设置与试听、阅读辅助和数据管理等功能。

### 更快的查词：Dictionary + Quick Context + AI

过去普通词义较大程度依赖 AI，因此简单查词也可能受到生成速度影响；AI 有时还会把“当前单词”和它所在的短语一起解释，例如形容词和后面的名词都显示成同一整段短语，让人难以判断哪个释义对应哪个词。

现在把查词职责拆成三层：

1. **Dictionary（字典）**：快速提供基础词义、词性、词形、IPA 和发音等较稳定的词典信息。
2. **Quick Context（快速语境）**：使用**完整当前句子**进行快速、非生成式的语境翻译，再取出当前查词单位在该句中的意思。
3. **AI Detail（AI 深度解释）**：继续负责语法、复杂用法、句子分析和更深入的解释。

因此，普通查词不再大幅依赖 AI 的生成速度，同时又保留 AI 在复杂理解上的优势。

有可用释义时，用户还可以在词汇管理中检查、编辑或删除已保存的释义，而不必把不同来源的含义强行合并。

### “单词爆炸”更快

“单词爆炸”中每个可见单词的小释义，在正常路径下不再分别等待一次 AI 请求，而是优先使用 Quick Context，并保留已有的学习释义。

整句翻译和更深入的 AI 分析仍然保留。

### 延续并增强断句与句子选择

本次继续保留 LingKuma 原有的句子处理能力，并针对 Calibre 的 EPUB 阅读环境进一步改进：

- 改进 EPUB 中跨行、跨文本节点的句子选取；
- 减少只取半句或误跨句的问题；
- 更保守地处理缩写、首字母、数字小数、引号、括号、冒号和分号；
- 修复明显由 EPUB 排版断行造成的连字符断词；
- 改进有意义的日文、韩文短句的识别。

Calibre 移植版不自动转换或处理 PDF。PDF 阅读可使用原版 LingKuma 浏览器插件。

### 支持带横杠的复合词

过去下面这类词可能会被错误拆开：

- `well-known`
- `out-of-sample`
- `peer-on-peer`

现在会尽可能把这种显式英文连字符复合词视为一个完整的查词和学习单位。

而 `inter-` + 换行 + `national` 这种由排版断行造成的情况仍然单独处理，并在明确时保守修复为 `international`。

### 发音：字典真人发音 + IPA + 美音 / 英音

英语查词优先使用可靠的字典发音数据：

- 有可靠数据时显示当前实际词形的 IPA；
- 美音和英音可以分别显示并独立播放；
- 有字典真人录音时优先使用真人录音；
- 当前实际词形没有录音时，再使用 TTS。

最上方单词的默认发音规则为：

- 只有美音录音 → 播放美音；
- 只有英音录音 → 播放英音；
- 美音和英音都有 → **默认美音**；
- 两种录音都没有 → 使用 TTS 兜底。

这对 `books`、`worked`、`studies`、`working` 等 `-s / -ed / -ing` 实际词形尤其重要。

### 修复 Calibre 中的 Edge TTS

**Edge TTS 是 LingKuma 原版已经具备的功能，并非本次新增的语音渠道。**

本次主要修复它在 Calibre 运行环境中的兼容性问题，改进语音合成、试听、参数传递和停止播放的处理，并使用内置的 `edge-tts` 客户端及所需依赖。

在 Windows Calibre 9.16 的实际安装测试中，用户已确认：

- Edge TTS 美音可以正常朗读；
- Edge TTS 英音可以正常朗读；
- 停止播放按钮工作正常。

Calibre 设置中也提供系统本地语音、Edge TTS 和 GPT TTS 的配置及试听入口。不同语音渠道继续使用各自的配置和服务要求。

### 阅读与学习功能继续保留

本次升级继续保留或恢复适用于 Calibre 的 LingKuma 阅读工作流，包括：

- 生词 / 熟词状态与保存的词义；
- 例句与学习记录；
- AI 句子分析和更深入的单词解释；
- Bionic Reading；
- Reading Ruler；
- POS Highlight；
- 自定义外部搜索 / 词典 / 百科按钮；
- 本地词库管理；
- WebDAV 备份 / 恢复；
- EPUB 阅读与文本修复；
- Calibre 兼容的主题和弹窗行为；
- 章节导航、阅读进度及页面外观设置。

## 当前语言范围

LingKuma 原项目仍然是多语言工具，但这次新增的**本地字典加速目前主要针对英语源文本**。

本版本中：

- 内置本地词典是 **英语 → 简体中文**；
- Quick Context 在服务支持的情况下可以按照用户设置的目标语言工作；
- 其他源语言仍可使用适用的翻译与 AI 功能；
- 其他源语言对应的本地字典包目前还没有一起加入。

因此，这一版最明显的速度与词义稳定性提升集中在**英语源文本阅读**。其他源语言不会因为缺少对应的本地词典，就失去原有的翻译与 AI 功能。

## 安装

1. 从 **[GitHub Releases](https://github.com/white-ink-cell/lingkuma-calibre/releases)** 下载 `lingkuma-calibre-1.1.2.zip`。
2. 打开 **Calibre → 首选项 → 插件**。
3. 选择 **从文件加载插件**。
4. 选择下载的 `lingkuma-calibre-1.1.2.zip` 文件。
5. 按 Calibre 的提示确认安装，并重启 Calibre。

> 不要将 GitHub 自动生成的 `Source code (zip)` 作为 Calibre 插件安装。请使用 Release 中提供的 `lingkuma-calibre-1.1.2.zip` 文件。

## 其他版本

- [LingKuma for Zotero](https://github.com/white-ink-cell/lingkuma-zotero)
- [LingKuma](https://github.com/lingkuma/LingKuma)

## 支持环境

- **Windows x64**
- 最低要求 **Calibre 9.16**
- 已在 Windows Calibre 9.16 / Python 3.14 环境中测试
- 支持 EPUB 阅读
- 本移植版不自动转换或处理 PDF
- **macOS 和 Linux 不在本次发布的支持范围内**

随包提供的 Edge TTS 原生依赖适用于 Windows AMD64 / Python 3.14。

## 设置

设置界面已经集成到 Calibre 中。

安装后，可通过 Calibre 中的 **LingKuma → 完整设置** 打开设置页面。

当前包括语言和翻译设置、AI Provider / 提示词、词汇管理、Dictionary、本地 / Edge / GPT TTS、弹窗与阅读辅助，以及可选的 WebDAV 备份 / 恢复。

界面语言与翻译目标语言可以分别设置，切换界面语言不会自动改变翻译目标。

## 隐私

LingKuma for Calibre 将本地状态存储在 Calibre 插件数据目录中。

使用翻译、AI、远程 TTS 或 WebDAV 时，插件可能向所选择的外部服务发送完成相应功能所必需的文本或数据。

普通单词或句子查词不会主动上传整本电子书。

## 上游项目与署名

- 原项目：**[LingKuma](https://github.com/lingkuma/LingKuma)**
- LingKuma Wiki：**[docs.lingkuma.org](https://docs.lingkuma.org)**
- 上游版本：**LingKuma 1.1.1**
- Calibre 移植版维护与发布：**white-ink-cell**

本仓库提供 LingKuma 的非官方 Calibre 移植版。

该移植版使 LingKuma 能够适配 Calibre 的阅读环境，同时尽可能保留原项目的核心功能、界面、资源和整体设计。Calibre 专用修改主要集中在运行环境兼容、句子选取、Dictionary / Quick Context、发音适配、复合词处理、磨砂玻璃效果以及多语言翻译支持。

更多信息请参阅 [UPSTREAM.md](../UPSTREAM.md)。

## 字典数据

内置英语词典基于 **English Wiktionary** 贡献者数据，经 **Wiktextract** 提取并由 **Kaikki.org** 分发的数据生成。

词典文本数据按照 **CC BY-SA 4.0** 分发。远程 Wikimedia Commons 发音文件继续遵循其来源页面所标注的独立许可证。

详见 `licenses/ENGLISH-WIKTIONARY-DATA-NOTICE.txt` 和 `THIRD-PARTY-NOTICES.txt`。

## 许可证

原 LingKuma 项目的作者署名、版权和许可证保持不变。

Calibre 适配器和兼容层使用 `licenses/LICENSE-ADAPTER.txt` 中的许可证。原 LingKuma 的许可证保留在 `LICENSE-LINGKUMA.txt` 中，随项目一起提供的第三方许可证和声明记录在 `THIRD-PARTY-NOTICES.txt` 中。
