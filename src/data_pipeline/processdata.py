import pdfplumber
import re
import json
import os

PDF_FILE_NAME = "luatanm2025.pdf" 

def extract_text_from_pdf(pdf_path):
    print(f"1️⃣ Đang đọc PDF: {pdf_path}...")
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text: full_text += text + "\n"
                if (i+1) % 10 == 0: print(f"   ... Đã đọc {i+1}/{total_pages} trang")
        print(f"✅ Đọc xong! Tổng số ký tự: {len(full_text)}")
        return full_text
    except Exception as e:
        print(f"❌ Lỗi đọc PDF: {e}")
        return None

def parse_law_text_robust(text):
    print("2️⃣ Đang phân tích cấu trúc...")
    output = { "metadata": {}, "content": [] }
    lines = text.split('\n')
    
    current_chapter = None
    current_article = None
    current_clause = None
    

    # Chấp nhận cả "Chương 1" (số thường) và "Chương I" (La mã)
    re_chapter = r"^Chương\s+([0-9IVX]+)" 
    # Chấp nhận cả "Điều 1.", "Điều 1:", hoặc "Điều 1" (không dấu)
    re_article = r"^Điều\s+(\d+)[\.:]?\s+(.*)"
    # Chấp nhận "1.", "1)", "1 "
    re_clause = r"^(\d+)[\.\)]\s+(.*)"
    
    count_articles = 0 # Đếm số điều tìm đước

    for line in lines:
        line = line.strip()
        if not line: continue

        # Tìm Chương
        chapter_match = re.match(re_chapter, line, re.IGNORECASE)
        if chapter_match:
            current_chapter = {
                "chapter_number": chapter_match.group(1),
                "chapter_title": "",
                "articles": []
            }
            output["content"].append(current_chapter)
            current_article = None
            continue

        # Tìm Điều
        article_match = re.match(re_article, line)
        if article_match:
            current_article = {
                "article_id": f"Dieu_{article_match.group(1)}",
                "article_title": line,
                "clauses": [],
                "text_intro": ""
            }
            if current_chapter:
                current_chapter["articles"].append(current_article)
            else:
                # Nếu không có chương, tạo một chương ảo để chứa
                if not output["content"]:
                    output["content"].append({"chapter_number": "Unknown", "chapter_title": "", "articles": []})
                output["content"][-1]["articles"].append(current_article)
            
            current_clause = None
            count_articles += 1
            continue

        # Tìm Khoản
        clause_match = re.match(re_clause, line)
        if clause_match and current_article:
            current_clause = {
                "clause_id": clause_match.group(1),
                "text": clause_match.group(2)
            }
            current_article["clauses"].append(current_clause)
            continue

        # Gộp nội dung (Text Accumulation)
        if current_chapter and not current_article:
            current_chapter["chapter_title"] += " " + line
        elif current_article and current_clause:
            current_clause["text"] += " " + line
        elif current_article:
            current_article["text_intro"] += " " + line

    print(f"✅ Phân tích xong! Tìm thấy {count_articles} điều luật.")
    return output

# --- CHẠY ---
if __name__ == "__main__":
    input_dir = "data/rawData"
    output_dir = "data/processData"
    
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(input_dir, PDF_FILE_NAME)
    
    if os.path.exists(pdf_path):
        raw_text = extract_text_from_pdf(pdf_path)
        if raw_text:
            data = parse_law_text_robust(raw_text)
            
            # Xuất file
            output_name = PDF_FILE_NAME.replace(".pdf", "_processed.json")
            output_path = os.path.join(output_dir, output_name)
            
            print(f"3️⃣ Đang ghi file: {output_name}...")
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"THÀNH CÔNG! File đã được lưu tại:\n {output_path}")
            except Exception as e:
                print(f"Lỗi khi ghi file: {e}")
    else:
        print(f"Không tìm thấy file '{PDF_FILE_NAME}' trong thư mục này!")
        print("Hãy kiểm tra lại xem bạn đã upload file PDF chưa?")