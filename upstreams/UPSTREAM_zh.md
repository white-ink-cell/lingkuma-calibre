# 上游项目与移植说明

[English](UPSTREAM.md) | **简体中文** | [日本語](UPSTREAM_ja.md) | [한국어](UPSTREAM_ko.md)

本项目是 **LingKuma 1.1.0** 的非官方 Calibre 移植版。

- 原项目：`lingkuma/LingKuma`
- 上游版本：LingKuma 1.1.0
- Calibre 移植版维护 / 发布：`white-ink-cell`

LingKuma 原项目的作者、版权、许可证和随项目分发的上游资源保持不变。

## 移植版主要改动

Calibre 移植版主要增加：

1. LingKuma 外部的 Calibre / Qt WebEngine 兼容层。
2. 适用于 Calibre 阅读内容的句子边界判断和文本重建规则。1.0 还支持日文、韩文中有意义的少于 5 个字符的短句或短语：当其包含不止一个词汇单位时，也可以触发 Word Explosion。
3. 在保留 LingKuma 原主题和弹窗逻辑的同时，增加 Calibre 可用的磨砂玻璃兼容效果。
4. 增加源语言和目标语言适配，用于多语言翻译、AI 输出及相关语言元数据。

Calibre 专用功能尽量放在 adapter / host / compatibility 层中；随项目分发的 LingKuma 上游资源继续保留原有署名和许可证。
