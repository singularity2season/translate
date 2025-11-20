# PDF Automatic Translator (GROBID + DeepL)

このツールは、指定したフォルダ内のPDFファイルから**本文テキストのみを抽出**し、**DeepL APIを使用して日本語に翻訳**するPythonスクリプトです。

論文やレポートなどのPDFから、レイアウト情報（図表やヘッダー・フッターなど）を除去し、純粋なテキストとして翻訳したい場合に最適です。

## 🚀 主な機能

  * **高度なテキスト抽出**: [GROBID](https://github.com/kermitt2/grobid) を使用して、PDFから構造化された本文テキストを抽出します。
  * **高精度な翻訳**: DeepL APIを使用し、抽出した英文を自然な日本語に翻訳します。
  * **スマート処理**:
      * 翻訳済みのファイルは自動的にスキップ（API使用量の節約）。
      * 長文は段落ごとに分割して翻訳し、APIレート制限を回避。
  * **中間ファイル保存**: 抽出した英文テキストやXMLデータも保存されるため、原文確認が容易です。

## 🛠️ 必要要件 (Prerequisites)

  * **Python 3.8+**
  * **DeepL API Key** (Free または Pro)
  * **GROBID サーバー** (ローカルまたはリモートで稼働していること)

## 📦 インストール & セットアップ

### 1\. ライブラリのインストール

必要なPythonライブラリをインストールします。

```bash
pip install requests python-dotenv
```

### 2\. GROBIDの起動

このツールはPDF解析にGROBIDを使用します。Dockerを使用して起動するのが最も簡単です。

```bash
# Dockerを使ってGROBIDサーバーを立ち上げる（ポート8070）
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

※ Docker環境がない場合は、[GROBID公式サイト](https://grobid.readthedocs.io/)の手順に従ってインストールしてください。

### 3\. 環境変数の設定 (.env)

スクリプトと同じディレクトリに `.env` ファイルを作成し、以下の内容を記述してください。

```ini
# .env file

# 【必須】DeepLのAPIキー
DEEPL_API_KEY=your_deepl_api_key_here

# 【任意】DeepL APIのURL（Pro版の場合は変更してください）
# Free版: https://api-free.deepl.com/v2/translate
# Pro版 : https://api.deepl.com/v2/translate
DEEPL_API_URL=https://api-free.deepl.com/v2/translate

# 【任意】GROBIDのURL（デフォルトはローカルホスト）
GROBID_API_URL=http://localhost:8070/api/processFulltextDocument
```

### 4\. フォルダの準備

スクリプトと同じ階層に、入力用ディレクトリを作成します（出力用は自動生成されます）。

```bash
mkdir input_pdf
```

## 📖 使い方

1.  翻訳したいPDFファイルを `input_pdf` フォルダに配置します。
2.  スクリプトを実行します。

<!-- end list -->

```bash
python main.py
```

3.  処理が完了すると `output_pdf` フォルダに結果が保存されます。

### 📂 出力ディレクトリ構成

```text
output_pdf/
├── xml/        # GROBIDが解析した構造化XMLデータ
├── en_txt/     # PDFから抽出された英語本文テキスト
└── jp_txt/     # DeepLによって翻訳された日本語テキスト (★最終成果物)
```

## ⚠️ 注意点

  * **DeepLの文字数制限**: Free版APIには月間50万文字の上限があります。大量の論文を処理する場合はご注意ください。
  * **翻訳精度**: 数式や特殊な記号が多い箇所は、意図しない翻訳になる場合があります。
  * **GROBIDのタイムアウト**: 非常に重いPDFや複雑なPDFの場合、GROBIDの解析がタイムアウトする可能性があります（コード内の `GROBID_TIMEOUT` で調整可能）。

## 📝 ライセンス

This project is licensed under the terms of the MIT license.