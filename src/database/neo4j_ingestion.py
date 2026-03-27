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

    id_to_node = {}
    
    # --- XỬ LÝ NODES ---
    for node in nodes:
        node_id = node.get("id")
        label = node.get("label", "Khac").replace(" ", "_") 
        name = node.get("name", "").strip()
        
        # BƯỚC 2: Lấy nội dung gốc từ JSON (nếu không có thì để trống)
        raw_content = node.get("raw_content", "").strip()
        
        id_to_node[node_id] = {"label": label, "name": name}

        query = f"""
        MERGE (n:{label} {{name: $name}})
        SET n.raw_content = $raw_content
        """
        tx.run(query, name=name, raw_content=raw_content)    

    # --- XỬ LÝ EDGES (QUAN HỆ) --- 
    for edge in edges:
        source_id = edge.get("source")
        target_id = edge.get("target")
        rel_type = edge.get("type", "LIEN_QUAN").replace(" ", "_").upper()

        if source_id in id_to_node and target_id in id_to_node:
            source_node = id_to_node[source_id]
            target_node = id_to_node[target_id]

            query = f"""
            MATCH (a:{source_node['label']} {{name: $source_name}})
            MATCH (b:{target_node['label']} {{name: $target_name}})
            MERGE (a)-[r:{rel_type}]->(b)
            """
            tx.run(query, source_name=source_node['name'], target_name=target_node['name'])

# ==========================================
# 3.HÀM MAIN
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
                # Chạy hàm ingest_data bên trong một transaction của Neo4j để có tính toàn vẹn dữ liệu
                session.execute_write(ingest_data, graph)

    print("\nTuyệt vời! Đã nạp thành công toàn bộ dữ liệu lên Neo4j.")
    driver.close()

if __name__ == "__main__":
    main()