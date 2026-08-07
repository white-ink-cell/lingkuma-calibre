# 上流プロジェクトと移植について

[English](UPSTREAM.md) | [简体中文](UPSTREAM_zh.md) | **日本語** | [한국어](UPSTREAM_ko.md)

このプロジェクトは **LingKuma 1.1.0** の非公式 Calibre 移植版です。

- 元プロジェクト：`lingkuma/LingKuma`
- 上流バージョン：LingKuma 1.1.0
- Calibre 移植版のメンテナンス / 公開：`white-ink-cell`

LingKuma 原プロジェクトの作者表記、著作権、ライセンス、同梱される上流リソースは変更していません。

## 移植版の主な変更

Calibre 移植版では主に次を追加しています。

1. LingKuma の外側に配置する Calibre / Qt WebEngine 互換レイヤー。
2. Calibre の読書内容向けの文境界判定とテキスト再構築。1.0 では、日本語・韓国語の 5 文字未満の意味のある短文・短いフレーズも、複数の語彙単位を含む場合は Word Explosion を開けます。
3. LingKuma 本来のテーマとポップアップロジックを維持したまま利用する、Calibre 対応のすりガラス表示。
4. 多言語翻訳、AI 出力、関連する言語情報のための入力言語・翻訳先言語処理。

Calibre 固有の処理は可能な限り adapter / host / compatibility レイヤーに分離し、同梱される LingKuma 上流リソースの原署名とライセンスを維持しています。
