import json

def check_graph_quality():
    # 1. Đọc file gốc
    with open('data/processData/luatanm2025_processed.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 2. Đọc file đồ thị
    with open('data/processData/extracted_knowledge_graph.json', 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    # Lấy danh sách ID Điều luật từ file gốc
    raw_articles = []
    for chapter in raw_data.get("content", []):
        for article in chapter.get("articles", []):
            raw_articles.append(article.get("article_id"))

    print(f"📊 BÁO CÁO KIỂM TRA DỮ LIỆU:")
    print(f"- Tổng số Điều trong file gốc: {len(raw_articles)}")
    print(f"- Tổng số Điều đã trích xuất graph: {len(graph_data)}")

    # Kiểm tra Điều nào bị sót
    extracted_ids = [item.get("article_id") for item in graph_data]
    missing_articles = set(raw_articles) - set(extracted_ids)
    if missing_articles:
        print(f"\n❌ CẢNH BÁO: Đang bị sót các Điều sau chưa được trích xuất: {missing_articles}")
    else:
        print("\n✅ Tuyệt vời: Không bị sót Điều luật nào!")

    # Kiểm tra chất lượng (Điều nào bị trích xuất quá ít Node/Edge)
    print("\n⚠️ Cảnh báo các Điều có khả năng bị trích xuất sơ sài (Dưới 3 Node hoặc 3 Edge):")
    for item in graph_data:
        article_id = item.get("article_id")
        graph = item.get("graph", {})
        if graph: # Đảm bảo graph không phải là None
            nodes_count = len(graph.get("nodes", []))
            edges_count = len(graph.get("edges", []))
            if nodes_count < 3 or edges_count < 3:
                print(f"  -> {article_id}: Chỉ có {nodes_count} Nodes và {edges_count} Edges.")

if __name__ == "__main__":
    check_graph_quality()