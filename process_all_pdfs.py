import requests
import os
import glob
import xml.etree.ElementTree as ET
import time
from dotenv import load_dotenv  # 追加: .env読み込み用

# --- ▼ 設定エリア (環境変数から読み込み) ▼ ---

# 1. .envファイルを読み込む
load_dotenv()

# 2. 環境変数を取得
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
DEEPL_URL = os.getenv("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate") # デフォルトはFree版
GROBID_URL = os.getenv("GROBID_API_URL", "http://localhost:8070/api/processFulltextDocument")

# その他の設定
TARGET_LANG = "JA"
GROBID_TIMEOUT = 180  # 秒
INPUT_DIR = "input_pdf"
OUTPUT_DIR = "output_pdf"

# APIキーの存在チェック
if not DEEPL_API_KEY:
    print("❌ エラー: .envファイルが見つからないか、DEEPL_API_KEYが設定されていません。")
    print("   同じフォルダに .env ファイルを作成し、APIキーを記述してください。")
    exit(1)

# ------------------------------------------------

# 出力用サブフォルダ
OUTPUT_XML_DIR = os.path.join(OUTPUT_DIR, "xml")
OUTPUT_TXT_DIR = os.path.join(OUTPUT_DIR, "en_txt")
OUTPUT_JP_DIR  = os.path.join(OUTPUT_DIR, "jp_txt")
NAMESPACES = {'tei': 'http://www.tei-c.org/ns/1.0'}

def setup_directories():
    os.makedirs(OUTPUT_XML_DIR, exist_ok=True)
    os.makedirs(OUTPUT_TXT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_JP_DIR, exist_ok=True)

def translate_text_via_deepl(text):
    """DeepL APIを使ってテキストを翻訳する関数"""
    if not text or not text.strip():
        return ""

    params = {
        "auth_key": DEEPL_API_KEY,
        "text": text,
        "target_lang": TARGET_LANG
    }

    try:
        response = requests.post(DEEPL_URL, data=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["translations"][0]["text"]
        elif response.status_code == 403:
            print("  ⚠️ DeepL認証エラー: APIキーが間違っているか、無効です。")
            return "[Translation Error: Invalid API Key]"
        elif response.status_code == 456:
            print("  ⚠️ DeepL上限到達: 月間の翻訳文字数制限を超えました。")
            return "[Translation Error: Quota Exceeded]"
        else:
            print(f"  ⚠️ DeepLエラー: {response.status_code} - {response.text}")
            return f"[Translation Error: {response.status_code}]"
            
    except Exception as e:
        print(f"  ⚠️ 翻訳通信エラー: {e}")
        return "[Translation Error: Connection Failed]"

def translate_long_text(full_text):
    """長文をDeepLに送るためのスマートなラッパー関数"""
    paragraphs = full_text.split("\n\n")
    translated_paragraphs = []
    
    print(f"  🤖 翻訳開始: 全 {len(paragraphs)} 段落を処理します...")

    for i, para in enumerate(paragraphs):
        if not para.strip():
            continue
        
        trans = translate_text_via_deepl(para)
        translated_paragraphs.append(trans)
        
        time.sleep(0.5) # APIレート制限対策
        
        if (i + 1) % 10 == 0:
            print(f"     ... {i + 1}/{len(paragraphs)} 段落完了")

    return "\n\n".join(translated_paragraphs)

def extract_body_from_xml(xml_content):
    """XMLから本文抽出"""
    try:
        root = ET.fromstring(xml_content)
        body_text_list = []
        paragraphs = root.findall('.//tei:text//tei:p', NAMESPACES)
        if not paragraphs: return None
        
        for p in paragraphs:
            text_segments = [seg for seg in p.itertext()]
            full_p_text = "".join(text_segments).strip()
            if full_p_text:
                body_text_list.append(full_p_text)
        return "\n\n".join(body_text_list)
    except:
        return None

def process_single_pdf(pdf_path):
    base_filename = os.path.basename(pdf_path).replace(".pdf", "")
    
    xml_path = os.path.join(OUTPUT_XML_DIR, f"{base_filename}.xml")
    en_txt_path = os.path.join(OUTPUT_TXT_DIR, f"{base_filename}_en.txt")
    jp_txt_path = os.path.join(OUTPUT_JP_DIR, f"{base_filename}_jp.txt")

    # スマート機能: 翻訳済みなら完全スキップ
    if os.path.exists(jp_txt_path):
        print(f"\n⏭️  完全スキップ (翻訳済み): {base_filename}")
        return "SKIPPED"

    print(f"\n🔄 処理開始: {base_filename}")

    english_text = ""
    
    # 既存の英語テキストがあれば使用
    if os.path.exists(en_txt_path):
        print("  📂 既存の英語テキストを使用します。")
        with open(en_txt_path, "r", encoding="utf-8") as f:
            english_text = f.read()
    else:
        # GROBID実行
        try:
            with open(pdf_path, 'rb') as f:
                files = {'input': f}
                resp = requests.post(GROBID_URL, files=files, data={'consolidateHeader': '1'}, timeout=GROBID_TIMEOUT)
            
            if resp.status_code != 200:
                print(f"  ❌ GROBIDエラー: {resp.status_code}")
                return False
            
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            
            english_text = extract_body_from_xml(resp.text)
            if not english_text:
                print("  ⚠️ 本文が抽出できませんでした。")
                return False
                
            with open(en_txt_path, "w", encoding="utf-8") as f:
                f.write(english_text)
            print("  ✅ 本文抽出完了 (English)")

        except Exception as e:
            print(f"  ❌ GROBID接続/処理エラー: {e}")
            return False

    # DeepL翻訳
    print("  🌍 日本語へ翻訳中... (時間がかかります)")
    japanese_text = translate_long_text(english_text)
    
    if "[Translation Error" in japanese_text and len(japanese_text) < 100:
        print("  ❌ 翻訳に失敗しました。")
        return False

    with open(jp_txt_path, "w", encoding="utf-8") as f:
        f.write(japanese_text)
    
    print(f"  🎉 翻訳保存完了: {os.path.basename(jp_txt_path)}")
    return True

def main():
    setup_directories()
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    
    if not pdf_files:
        print(f"'{INPUT_DIR}' にPDFがありません。")
        return

    print(f"--- {len(pdf_files)} 件のPDFを一括処理します (抽出 & 翻訳) ---")
    print(f"--- API KEY: {DEEPL_API_KEY[:5]}... (Masked) ---")
    
    for pdf in pdf_files:
        process_single_pdf(pdf)

    print("\n--- 全ての処理が完了しました ---")

if __name__ == "__main__":
    main()