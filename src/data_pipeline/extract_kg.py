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

# SỬA LẠI TÊN MODEL CHUẨN ĐANG HOẠT ĐỘNG
model = genai.GenerativeModel('gemini-2.5-flash') 

SYSTEM_PROMPT = """
Bạn là một chuyên gia AI về Kỹ thuật tri thức. Hãy đọc văn bản luật và trích xuất Thực thể (Nodes) và Quan hệ (Edges) theo định dạng JSON.

DANH SÁCH BẮT BUỘC (KHÔNG DÙNG TỪ KHÁC):
- Node Labels: VanBanLuat, Chuong, Dieu, Khoan, KhaiNiem, ChuThe, HanhViCam, HeThongThongTin, BienPhapBaoVe, TrachNhiem, NghiaVu, SanPhamDichVu.
- Edge Types: BAO_GOM, DINH_NGHIA, NGHIEM_CAM, QUY_DINH_TRACH_NHIEM, THUC_HIEN, AP_DUNG, PHOI_HOP_VOI, CUNG_CAP, QUAN_LY, GAY_HAI_CHO, BAO_VE, IS_A.

QUY TẮC:
1. Không bịa đặt thông tin.
2. Tên Node (name) phải ngắn gọn, súc tích.
3. Nếu văn bản ghi "Luật này", hãy ghi rõ là "Luật An ninh mạng".

CẤU TRÚC JSON BẮT BUỘC TRẢ VỀ:
{
  "nodes": [{"id": "duy_nhat", "label": "Nhan", "name": "Ten"}],
  "edges": [{"source": "id_nguon", "target": "id_dich", "type": "LOAI_QUAN_HE"}]
}
"""

def extract_graph_from_text(text_content):
    """Gửi nội dung luật cho Gemini và nhận về JSON Graph (Tích hợp Exponential Backoff)"""
    full_prompt = f"{SYSTEM_PROMPT}\n\nVĂN BẢN CẦN TRÍCH XUẤT:\n{text_content}"
    
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
                # Kỹ thuật Exponential Backoff: Lần 1 đợi 60s, Lần 2 đợi 120s, Lần 3 đợi 240s
                sleep_time = base_sleep_time * (2 ** attempt)
                print(f"  [!] Đụng giới hạn API (Rate limit). Đang nghỉ {sleep_time} giây trước khi thử lại... (Lần {attempt + 1}/{max_retries})")
                time.sleep(sleep_time) 
            else:
                print(f"  [!] Lỗi không xác định: {error_msg}")
                return None
                
    print("  [!] Đã thử lại 3 lần nhưng vẫn thất bại. Bỏ qua Điều luật này.")
    return None

def main():
    # 1. Đọc file JSON dữ liệu thô (Source)
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
            
            # KỸ THUẬT RESUME: Kiểm tra xem Điều này đã trích xuất thành công chưa
            if article_id in extracted_article_ids:
                print(f" -> Bỏ qua: {article_title} (Đã có sẵn)")
                continue # Nhảy qua vòng lặp tiếp theo, không gọi Gemini nữa
            
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