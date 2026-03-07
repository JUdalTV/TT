import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# ==========================================
# 1. TẢI CẤU HÌNH TỪ FILE .ENV
# ==========================================
load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

if not PASSWORD:
    raise ValueError("Chưa có mật khẩu Neo4j. Vui lòng kiểm tra file .env!")

# Khởi tạo kết nối với Database
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# ==========================================
# 2. HÀM XỬ LÝ VÀ ĐẨY DỮ LIỆU
# ==========================================
def ingest_data(tx, graph_data):
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    # Tạo từ điển (Dictionary) để map ID cục bộ của JSON với Tên thực thể
    # Kỹ thuật này giúp gộp các node trùng tên (Ví dụ: "Bộ Công an" ở nhiều điều luật sẽ là 1 node)
    id_to_node = {}
    
    # --- XỬ LÝ NODES ---
    for node in nodes:
        node_id = node.get("id")
        # Chuẩn hóa nhãn (label) không có khoảng trắng
        label = node.get("label", "Khac").replace(" ", "_") 
        name = node.get("name", "").strip()
        
        id_to_node[node_id] = {"label": label, "name": name}

        # Dùng lệnh MERGE của Cypher: Nếu Node có tên này chưa tồn tại thì tạo mới, có rồi thì bỏ qua
        query = f"MERGE (n:{label} {{name: $name}})"
        tx.run(query, name=name)

    # --- XỬ LÝ EDGES (QUAN HỆ) ---
    for edge in edges:
        source_id = edge.get("source")
        target_id = edge.get("target")
        # Chuẩn hóa tên quan hệ: VIẾT HOA và dùng DẤU GẠCH DƯỚI
        rel_type = edge.get("type", "LIEN_QUAN").replace(" ", "_").upper()

        if source_id in id_to_node and target_id in id_to_node:
            source_node = id_to_node[source_id]
            target_node = id_to_node[target_id]

            # Dùng MATCH để tìm 2 Node đã tạo, sau đó MERGE để nối dây giữa chúng
            query = f"""
            MATCH (a:{source_node['label']} {{name: $source_name}})
            MATCH (b:{target_node['label']} {{name: $target_name}})
            MERGE (a)-[r:{rel_type}]->(b)
            """
            tx.run(query, source_name=source_node['name'], target_name=target_node['name'])

# ==========================================
# 3. HÀM CHÍNH (MAIN)
# ==========================================
def main():
    file_path = "data/processData/extracted_knowledge_graph.json"
    
    print("Đang đọc file dữ liệu Knowledge Graph...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {file_path}")
        return

    print("Bắt đầu đẩy dữ liệu lên Neo4j...")
    
    # Mở phiên làm việc với Neo4j
    with driver.session() as session:
        for item in data:
            article_id = item.get("article_id")
            print(f" -> Đang nạp {article_id}...")
            
            graph = item.get("graph", {})
            if graph:
                # Chạy hàm ingest_data bên trong một transaction của Neo4j
                session.execute_write(ingest_data, graph)

    print("\nTuyệt vời! Đã nạp thành công toàn bộ dữ liệu lên Neo4j.")
    driver.close()

if __name__ == "__main__":
    main()