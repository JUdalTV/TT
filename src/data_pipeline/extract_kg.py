import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load các biến môi trường từ file .env
load_dotenv()

# Lấy API key
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Không tìm thấy GEMINI_API_KEY. Vui lòng kiểm tra file .env!")

genai.configure(api_key=API_KEY)


model = genai.GenerativeModel('gemini-2.5-flash') 

SYSTEM_PROMPT = """Bạn là một chuyên gia pháp lý và Data Engineer siêu việt. Nhiệm vụ của bạn là đọc các Điều luật An ninh mạng và trích xuất ra một Knowledge Graph (Đồ thị tri thức) dưới định dạng JSON.

TUYỆT ĐỐI TUÂN THỦ CÁC QUY TẮC SAU:
1. KHÔNG ĐƯỢC TÓM TẮT: Phải giữ nguyên văn các từ khóa quan trọng. Không được gộp các hành vi hoặc trách nhiệm lại với nhau.
2. PHÂN CẤP TRIỆT ĐỂ (QUAN TRỌNG NHẤT): 
   - Nếu Điều luật có các Khoản (1, 2, 3...), bạn BẮT BUỘC phải tạo các Node riêng biệt có label là "Khoan" (VD: name: "Khoản 1 Điều 10").
   - Nếu Khoản có các Điểm (a, b, c...), BẮT BUỘC phải tạo Node label là "Diem" (VD: name: "Điểm a Khoản 1 Điều 10").
   - Dùng quan hệ "BAO_GOM" để nối Điều -> Khoản, và Khoản -> Điểm.
3. GẮN ĐÚNG CHỖ: Mọi Node như "HanhViCam", "TrachNhiem", "ChuThe" phải được nối trực tiếp vào cái "Khoan" hoặc "Diem" chứa nó, KHÔNG ĐƯỢC nối chung chung vào "Dieu".
4. LƯU GIỮ NGUYÊN VĂN (CỰC KỲ QUAN TRỌNG): Đối với các Node là "Dieu", "Khoan", "Diem", "KhaiNiem", bạn BẮT BUỘC phải tạo thêm một thuộc tính là "raw_content" và copy y xì đúc, không sai một dấu phẩy nội dung gốc của phần đó vào đây.

DANH SÁCH NODE LABELS CHO PHÉP:
- Dieu (Điều luật)
- Khoan (Khoản)
- Diem (Điểm)
- ChuThe (Ví dụ: Bộ Công an, Doanh nghiệp cung cấp dịch vụ...)
- HanhViCam (Hành vi bị nghiêm cấm)
- TrachNhiem (Trách nhiệm, nghĩa vụ phải làm)
- BienPhapBaoVe (Các biện pháp bảo vệ an ninh mạng)
- KhaiNiem (Giải thích từ ngữ)
- HeThongThongTin (Hệ thống thông tin quan trọng...)

DANH SÁCH RELATIONSHIP CHO PHÉP:
- BAO_GOM (Điều -> Khoản, Khoản -> Điểm)
- QUY_DINH_TRACH_NHIEM (Khoản/Điểm -> TrachNhiem)
- NGHIEM_CAM (Khoản/Điểm -> HanhViCam)
- THUC_HIEN (ChuThe -> TrachNhiem / BienPhapBaoVe)
- AP_DUNG (Khoản/Điểm -> BienPhapBaoVe)
- DINH_NGHIA (Khoản -> KhaiNiem)

ĐẦU RA BẮT BUỘC TRẢ VỀ CHUẨN JSON CÓ DẠNG:
{
  "nodes": [
    {
      "id": "node_1", 
      "label": "Khoan", 
      "name": "Khoản 1 Điều 10",
      "raw_content": "1. Hệ thống thông tin quan trọng về an ninh quốc gia là hệ thống thông tin khi bị sự cố, xâm nhập, chiếm quyền điều khiển..."
    }
  ],
  "edges": [{"source": "node_1", "target": "node_2", "type": "BAO_GOM"}]
}
"""

def extract_graph_from_text(text_content):
    """Gửi nội dung luật cho Gemini và nhận về JSON Graph (Tích hợp Exponential Backoff)"""
    
    # ==========================================
    user_prompt = f"""Hãy trích xuất đồ thị tri thức cho Điều luật sau. 
    CHÚ Ý: Hãy quét thật kỹ từng Khoản, từng Điểm (nếu có) và tạo Node tương ứng. Không được bỏ sót bất kỳ hành vi cấm hay trách nhiệm nào.

    Nội dung Điều luật:
    {text_content}
    """
    
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
    
    max_retries = 3 
    base_sleep_time = 60 # Thời gian nghỉ cơ bản là 60 giây
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json", 
                    temperature=0.1 
                )
            )
            graph_data = json.loads(response.text)
            return graph_data
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota" in error_msg:
                # Kỹ thuật Exponential Backoff
                sleep_time = base_sleep_time * (2 ** attempt)
                print(f"  [!] Đụng giới hạn API. Đang nghỉ {sleep_time} giây trước khi thử lại... (Lần {attempt + 1}/{max_retries})")
                time.sleep(sleep_time) 
            else:
                print(f"  [!] Lỗi không xác định: {error_msg}")
                return None
                
    print("  [!] Đã thử lại 3 lần nhưng vẫn thất bại. Bỏ qua Điều luật này.")
    return None

def main():
    # 1. Đọc file JSON Source
    try:
        with open('data/processData/luatanm2025_processed.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print("Không tìm thấy file nguồn luatanm2025_processed.json.")
        return

    # 2. Đọc file JSON đã trích xuất từ các lần chạy trước (Checkpoint)
    output_filename = "data/processData/extracted_knowledge_graph.json"
    all_extracted_graphs = []
    extracted_article_ids = set() # Dùng Set để lưu danh sách ID đã trích xuất

    if os.path.exists(output_filename):
        try:
            with open(output_filename, 'r', encoding='utf-8') as f:
                all_extracted_graphs = json.load(f)
                # Quét xem đã làm thành công những Điều nào
                for item in all_extracted_graphs:
                    extracted_article_ids.add(item.get("article_id"))
            print(f"[*] Đã tìm thấy {len(extracted_article_ids)} Điều luật được trích xuất từ trước.")
        except json.JSONDecodeError:
            print("[!] File kết quả cũ bị lỗi format, hệ thống sẽ tạo lại từ đầu.")

    print("\nBắt đầu tiến trình trích xuất (Tự động bỏ qua các Điều đã có)...")
    
    # 3. Duyệt qua từng Chương, Điều trong file JSON nguồn
    for chapter in raw_data.get("content", []):
        for article in chapter.get("articles", []):
            article_id = article.get("article_id")
            article_title = article.get("article_title", "")
            
            # Kiểm tra xem Điều này đã trích xuất thành công chưa
            if article_id in extracted_article_ids:
                print(f" -> Bỏ qua: {article_title} (Đã có sẵn)")
                continue 
            
            # Gộp text của toàn bộ các khoản trong 1 điều
            clauses_text = "\n".join([c.get("text", "") for c in article.get("clauses", [])])
            full_article_text = f"{article_title}\n{clauses_text}"
            
            print(f" -> Đang xử lý: {article_title}...")
            
            # Gọi API
            graph_result = extract_graph_from_text(full_article_text)
            
            if graph_result:
                all_extracted_graphs.append({
                    "article_id": article_id,
                    "graph": graph_result
                })
                
                # Cập nhật ID vào danh sách đã hoàn thành
                extracted_article_ids.add(article_id)
                
                # CHECKPOINT: Ghi file ngay lập tức sau khi thành công 1 điều luật
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(all_extracted_graphs, f, ensure_ascii=False, indent=2)
            
            # Thời gian nghỉ an toàn giữa các lượt bình thường
            time.sleep(15) 

    print(f"\nHoàn tất! Dữ liệu Knowledge Graph đã được lưu đầy đủ vào: {output_filename}")

if __name__ == "__main__":
    main()