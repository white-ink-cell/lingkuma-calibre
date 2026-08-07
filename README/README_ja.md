# LingKuma for Calibre

[English](README.md) | [简体中文](README_zh.md) | **日本語** | [한국어](README_ko.md)

オープンソースプロジェクト **LingKuma 1.1.0** を Calibre で利用できるようにした非公式のデスクトップ移植版です。ハイライト、単語検索、翻訳 / AI、文単位の解析、語彙管理、TTS、テーマ機能を Calibre の読書環境で利用できます。

> **Calibre 移植版の公開 / メンテナンス：[`white-ink-cell`](https://github.com/white-ink-cell)**  
> このリポジトリは LingKuma 公式の Calibre 版ではありません。LingKuma 原プロジェクトの作者表記、著作権、ライセンスは変更していません。`white-ink-cell` はこの Calibre 移植版の公開者・メンテナであることのみを示します。

## スクリーンショット

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

## 主な変更点

この移植版では、主に次の 4 点を Calibre 向けに調整しています。

### 1. Calibre 実行環境への対応

LingKuma の外側に Calibre 用の互換レイヤーを追加し、ブラウザー拡張環境に依存していた機能へ Calibre / Qt WebEngine で必要な実行機能を提供します。

可能な限り LingKuma 本来の機能とコード構造を維持しています。

### 2. 文選択の改善

Calibre の読書環境向けに文境界判定とテキスト再構築ルールを追加し、EPUB、PDF、括弧、略語、特殊な句読点を含む文章で完全な文を取得しやすくしています。

**1.0 の追加点：** 日本語・韓国語では、5 文字未満でも複数の語彙単位を含む意味のある短文・短いフレーズなら Word Explosion を開けます。単語 1 個だけの場合は従来どおり文として扱いません。

### 3. すりガラス効果への対応

LingKuma 原版の一部のガラス表現は、ブラウザー固有の Web コンポーネントや描画機能に依存しています。

この移植版では元の UI とテーマロジックを維持しつつ、Calibre の Qt WebEngine で利用できるすりガラス互換表示を提供します。

### 4. 多言語翻訳への対応

LingKuma 原版の一部の AI Prompt と言語処理経路は、中国語を固定の翻訳先として扱います。

この移植版では、入力言語の識別と翻訳先言語の処理を追加し、翻訳、AI 解説、TTS の言語情報、関連表示がユーザーの選択した言語に従うようにしています。

## インストール

1. **Calibre → 設定 → プラグイン** を開きます。
2. 旧版の LingKuma for Calibre がある場合は削除し、Calibre を完全に終了します。
3. Calibre を再起動し、**ファイルからプラグインを読み込む** を選択します。
4. GitHub Releases の `lingkuma-calibre-1.0.zip` をインストールします。
5. Calibre を再起動します。

> GitHub が自動生成する Source code ZIP を Calibre のプラグインとしてインストールしないでください。

## 翻訳設定

`LingKuma → Full Settings → AI / API Configuration`

利用可能なサービス：

- Google Web Translate（実験的、API キー不要）
- Microsoft Translator
- Google Cloud Translation
- LingKuma AI

## 対応形式と環境

直接開ける形式：

- EPUB
- HTMLZ
- TXT
- HTML / XHTML

その他の形式は Calibre で EPUB に変換できます。PDF の品質はテキストレイヤーと元のレイアウトに依存します。

動作環境：

- Calibre 7.0+
- Windows / macOS / Linux
- 主に Calibre 9.x でテスト

## データとプライバシー

設定、語彙、例文、読書進捗は Calibre のローカル設定ディレクトリに保存されます。

翻訳または AI サービスを利用する場合、処理に必要な単語、文、文脈のみが選択したサービスへ送信されます。電子書籍全体、Calibre の認証情報、ライブラリメタデータを意図的にアップロードすることはありません。

API キーはローカルのプラグイン状態ファイルに保存されます。WebDAV 同期はユーザーが明示的に実行した場合にのみ行われます。

## 上流プロジェクトとクレジット

- 元プロジェクト：**LingKuma**
- 上流バージョン：**LingKuma 1.1.0**
- Calibre 移植版のメンテナンス / 公開：**white-ink-cell**

LingKuma 原プロジェクトの作者表記、著作権、ライセンス、主要 UI、同梱上流リソースの帰属は変更していません。

詳細は [`UPSTREAM_ja.md`](UPSTREAM_ja.md) を参照してください。

## ライセンス

LingKuma 原プロジェクトの作者表記、著作権、ライセンスは変更していません。

Calibre アダプター / 互換レイヤーは `LICENSE-ADAPTER.txt`、LingKuma 原ライセンスは `LICENSE-LINGKUMA.txt`、第三者リソースのライセンスと通知は `THIRD-PARTY-NOTICES.txt` および `licenses/` を参照してください。
