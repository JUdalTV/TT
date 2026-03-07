import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate

# ==========================================
# 1. TẢI CẤU HÌNH BẢO MẬT
# ==========================================
load_dotenv()

# Kiểm tra các biến môi trường
if not os.getenv("GEMINI_API_KEY") or not os.getenv("NEO4J_PASSWORD"):
    raise ValueError("Thiếu API Key hoặc Mật khẩu Neo4j trong file .env!")

# ==========================================
# 2. KHỞI TẠO BỘ NÃO (GEMINI) VÀ NHÀ KHO (NEO4J)
# ==========================================
print("Đang khởi động AI và kết nối Database...")

# Khởi tạo Gemini (để temperature=0 để AI trả lời chính xác, không bịa đặt)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# Kết nối thẳng vào đồ thị Neo4j đang chạy
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD")
)

# ==========================================
# 3. TẠO PROMPT ÉP AI TRẢ LỜI TIẾNG VIỆT
# ==========================================
# Đôi khi AI tự động dịch sang tiếng Anh, ta cần ép nó dùng tiếng Việt
QA_PROMPT_TEMPLATE = """Bạn là một chuyên gia tư vấn Luật An ninh mạng Việt Nam. 
Hệ thống đã tự động quét đồ thị và trả về dữ liệu thô ở phần "Thông tin từ Database" bên dưới.

LƯU Ý CỰC KỲ QUAN TRỌNG: 
1. Bạn HÃY TIN TƯỞNG TUYỆT ĐỐI rằng dữ liệu trong "Thông tin từ Database" chính là câu trả lời chính xác cho câu hỏi của người dùng, dù nó có lặp lại từ khóa của câu hỏi hay không.
2. Hãy lấy dữ liệu thô đó, viết lại thành một câu trả lời tiếng Việt mạch lạc, dễ hiểu, trình bày theo dạng gạch đầu dòng (bullet points) cho đẹp mắt.
3. CHỈ KHI NÀO "Thông tin từ Database" là một danh sách rỗng (ví dụ: [] hoặc rỗng), bạn mới được nói "Tôi không tìm thấy thông tin này trong hệ thống".

Thông tin từ Database:
{context}

Câu hỏi: {question}
Câu trả lời (Bằng tiếng Việt):"""

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"], 
    template=QA_PROMPT_TEMPLATE
)
# ==========================================
# 3.5. TẠO PROMPT DẠY AI VIẾT CODE CYPHER THÔNG MINH
# ==========================================
CYPHER_GENERATION_TEMPLATE = """Bạn là một chuyên gia về Neo4j Cypher.
Hãy chuyển câu hỏi của người dùng thành câu lệnh Cypher để truy vấn đồ thị.
Chỉ sử dụng các Node và Relationship có trong Schema dưới đây:
{schema}

QUY TẮC BẮT BUỘC (RẤT QUAN TRỌNG):
1. KHI TÌM TÊN: Thường dùng toLower() và CONTAINS. NHƯNG CHÚ Ý: Nếu tìm 'Điều 1', hãy cẩn thận tránh nhầm với 'Điều 10', 'Điều 11'. Hãy dùng thủ thuật phù hợp.
2. KHI HỎI VỀ "NỘI DUNG": Nếu người dùng hỏi nội dung của Điều/Khoản, BẠN TUYỆT ĐỐI KHÔNG ĐƯỢC chỉ RETURN tên của node đó (Ví dụ: CẤM chỉ RETURN k.name).
3. CÁCH LẤY NỘI DUNG: Bạn BẮT BUỘC phải MATCH các node liên kết xung quanh nó và trả về các mối quan hệ.
Ví dụ nếu hỏi nội dung Khoản 1 Điều 10: 
MATCH (d:Dieu)-[:BAO_GOM]->(k:Khoan)-[r]->(n)
WHERE toLower(d.name) CONTAINS 'điều 10' AND toLower(k.name) CONTAINS 'khoản 1'
RETURN type(r) AS LoaiQuanHe, n.label AS LoaiThucThe, n.name AS ChiTietNoiDung

Câu hỏi: {question}
Câu lệnh Cypher:"""

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], 
    template=CYPHER_GENERATION_TEMPLATE
)
# ==========================================
# 4. KHỞI TẠO CẬU THƯ KÝ (LANGCHAIN)
# ==========================================
chain = GraphCypherQAChain.from_llm(
    cypher_llm=llm,          # Dùng Gemini để dịch Tiếng Việt sang lệnh Cypher
    qa_llm=llm,              # Dùng Gemini để tóm tắt kết quả thành câu trả lời
    graph=graph,             # Kết nối với Neo4j
    verbose=True,            # BẬT TRUE ĐỂ XEM AI TỰ VIẾT CODE CYPHER NHƯ THẾ NÀO (Rất hay!)
    qa_prompt=QA_PROMPT,
    cypher_prompt=CYPHER_PROMPT,
    return_intermediate_steps=True,
    allow_dangerous_requests=True
)

# ==========================================
# 5. GIAO DIỆN CHAT TRÊN TERMINAL
# ==========================================
def main():
    print("\n" + "="*50)
    print("🤖 HỆ THỐNG TRA CỨU LUẬT AN NINH MẠNG (GRAPHRAG)")
    print("Gõ 'quit' hoặc 'exit' để thoát.")
    print("="*50 + "\n")

    while True:
        user_question = input("\nBạn hỏi 🙋: ")
        
        if user_question.lower() in ['quit', 'exit', 'thoát']:
            print("Tạm biệt!")
            break
            
        if not user_question.strip():
            continue

        print("\nAI đang suy nghĩ và lục tìm đồ thị... 🔍")
        try:
            # Truyền câu hỏi cho LangChain xử lý
            response = chain.invoke({"query": user_question})
            print(f"\nAI trả lời 🤖: {response['result']}")
            
        except Exception as e:
            print(f"\n[!] Lỗi: Không thể trả lời câu hỏi này. Chi tiết: {e}")

if __name__ == "__main__":
    main()