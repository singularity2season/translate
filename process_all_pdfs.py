import requests
import os
import glob  # フォルダ内のファイルを検索するため
import xml.etree.ElementTree as ET
import time  # ログを見やすくするため

# --- 設定 ---
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
INPUT_DIR = "input_pdf"
OUTPUT_DIR = "output_pdf"

# 出力先フォルダ（XMLとTXTを分ける）
OUTPUT_XML_DIR = os.path.join(OUTPUT_DIR, "xml")
OUTPUT_TXT_DIR = os.path.join(OUTPUT_DIR, "txt")

# XMLの名前空間（GROBIDのTEI XMLを読むためのおまじない）
NAMESPACES = {'tei': 'http://www.tei-c.org/ns/1.0'}
# -----------

def setup_directories():
    """出力用のディレクトリが存在しなければ作成する"""
    os.makedirs(OUTPUT_XML_DIR, exist_ok=True)
    os.makedirs(OUTPUT_TXT_DIR, exist_ok=True)
    print(f"📁 入力フォルダ: {INPUT_DIR}")
    print(f"📁 出力フォルダ (TXT): {OUTPUT_TXT_DIR}")
    print(f"📁 出力フォルダ (XML): {OUTPUT_XML_DIR}")

def extract_body_from_xml(xml_content):
    """
    GROBIDが返したXML文字列（bytes or str）から本文（<p>タグ）を抽出する
    """
    try:
        # 文字列から直接XMLをパース
        root = ET.fromstring(xml_content)
        
        body_text_list = []
        
        # XPathを使って本文（<text>）の中の全パラグラフ（<p>）を検索
        paragraphs = root.findall('.//tei:text//tei:p', NAMESPACES)

        if not paragraphs:
            return None # 本文が見つからなかった
        
        for p in paragraphs:
            # タグ内のテキストを連結（改行や空白を保持しつつ）
            text_segments = [seg for seg in p.itertext()]
            full_p_text = "".join(text_segments).strip()
            if full_p_text:
                body_text_list.append(full_p_text)

        # 段落ごとに2行改行して結合
        return "\n\n".join(body_text_list)

    except ET.ParseError:
        print("  ❌ XMLパースエラー。XMLが不正かもしれません。")
        return None
    except Exception as e:
        print(f"  ❌ XML解析中に予期せぬエラー: {e}")
        return None

def process_single_pdf(pdf_path, output_txt_path, output_xml_path):
    """
    単一のPDFファイルをGROBIDに送信し、結果をXMLとTXTで保存する
    """
    print(f"\n🔄 処理中: {os.path.basename(pdf_path)}")
    
    try:
        # --- ステップ2: PDFをGROBIDに送信 ---
        with open(pdf_path, 'rb') as f:
            files = {'input': f}
            # (注) consolidateHeader=1 を指定すると書誌情報（著者など）の
            # 精度が上がることがありますが、必須ではありません。
            data = {'consolidateHeader': '1'}
            
            response = requests.post(GROBID_URL, files=files, data=data, timeout=300)

        if response.status_code != 200:
            print(f"  ❌ GROBIDエラー。 ステータス: {response.status_code}")
            return False

        xml_result = response.text
        
        # --- 機能: アウトプットの方法① (XML保存) ---
        with open(output_xml_path, "w", encoding="utf-8") as f:
            f.write(xml_result)
        print(f"  💾 XML保存完了: {os.path.basename(output_xml_path)}")
        
        # --- ステップ3: XMLから本文抽出 ---
        body_text = extract_body_from_xml(xml_result)
        
        if body_text:
            # --- 機能: アウトプットの方法② (TXT保存) ---
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(body_text)
            print(f"  💾 TXT保存完了: {os.path.basename(output_txt_path)}")
            return True
        else:
            print("  ⚠️ 本文(<p>タグ)がXMLから見つかりませんでした。")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ❌ エラー: GROBIDサーバーに接続できません。")
        print("      Dockerコンテナ (grobid_server) が起動しているか確認してください。")
        return "STOP" # 致命的なエラーなので処理を中断
    except requests.exceptions.Timeout:
        print(f"  ❌ タイムアウト: {os.path.basename(pdf_path)} の処理が時間切れになりました。")
        return False
    except Exception as e:
        print(f"  ❌ 予期せぬエラー: {e}")
        return False

def main():
    """メイン処理"""
    start_time = time.time()
    setup_directories()
    
    # 1. 入力フォルダ内の全PDFのパスを取得
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    
    if not pdf_files:
        print(f"\n‼️ '{INPUT_DIR}' フォルダに処理対象のPDFファイルが見つかりません。")
        return

    print(f"\n--- {len(pdf_files)} 件のPDFを対象に処理を開始します ---")
    
    processed_count = 0
    skipped_count = 0

    # 2. 全PDFをループ処理
    for pdf_path in pdf_files:
        
        # --- 機能: 出力名の決定 ---
        # (例: paper_A.pdf -> paper_A)
        base_filename = os.path.basename(pdf_path).replace(".pdf", "")
        
        # 出力先のフルパスを決定
        output_txt_path = os.path.join(OUTPUT_TXT_DIR, f"{base_filename}_body.txt")
        output_xml_path = os.path.join(OUTPUT_XML_DIR, f"{base_filename}.xml")

        # --- 機能: 重複処理の回避 ---
        # (TXTファイルが存在したら、処理済みとみなす)
        if os.path.exists(output_txt_path):
            print(f"\n⏭️  スキップ: {base_filename}_body.txt は既に存在します。")
            skipped_count += 1
            continue
            
        # 3. 未処理のPDFを処理
        result = process_single_pdf(pdf_path, output_txt_path, output_xml_path)
        
        if result == "STOP":
            print("\n🚨 サーバー接続エラーのため、処理を中断します。")
            break # ループを抜ける
        elif result:
            processed_count += 1

    # 4. 完了報告
    end_time = time.time()
    print("\n--- 処理が完了しました ---")
    print(f"✅ 処理成功: {processed_count} 件")
    print(f"⏭️ スキップ: {skipped_count} 件")
    print(f"⏱️ 合計時間: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    # GROBIDサーバーが起動しているか、簡易チェック
    try:
        requests.get("http://localhost:8070/api/version", timeout=30)
        #timeout=3は3秒以内に応答がない場合に例外を発生させる。
        print("GROBIDサーバー接続確認... OK")
        main()
    except requests.exceptions.ConnectionError:
        print("❌ 致命的エラー: GROBIDサーバー (http://localhost:8070) に接続できません。")
        print("   Dockerコンテナが -p 8070:8070 で起動しているか確認してください。")