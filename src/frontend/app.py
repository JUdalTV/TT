import streamlit as st
import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# ==========================================
# 1. CẤU HÌNH TRANG WEB STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Trợ lý Luật An Ninh Mạng",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Trợ lý ảo Luật An Ninh Mạng (GraphRAG)")
st.markdown("Hệ thống tra cứu pháp luật thông minh sử dụng **Knowledge Graph** và **Google Gemini**.")

# ==========================================
# 2. KHỞI TẠO BACKEND (CHỈ CHẠY 1 LẦN)
# ==========================================
# Dùng @st.cache_resource để trang web không phải kết nối lại Neo4j mỗi lần chat
@st.cache_resource
def init_graph_chain():
    load_dotenv()
    
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("NEO4J_PASSWORD"):
        st.error("⚠️ Thiếu API Key hoặc Mật khẩu Neo4j trong file .env!")
        st.stop()

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    # Prompt dịch Cypher (Phiên bản đã tối ưu ở Tuần 6)
    CYPHER_PROMPT = PromptTemplate(
        input_variables=["schema", "question"], 
        template="""Bạn là một chuyên gia về Neo4j Cypher.
        Hãy chuyển câu hỏi của người dùng thành câu lệnh Cypher để truy vấn đồ thị.
        Chỉ sử dụng các Node và Relationship có trong Schema dưới đây:
        {schema}
        
        QUY TẮC BẮT BUỘC:
        1. KHI TÌM TÊN: Dùng toLower() và CONTAINS. Tránh nhầm lẫn 'Điều 1' với 'Điều 10'.
        2. KHI HỎI VỀ "NỘI DUNG": KHÔNG ĐƯỢC chỉ RETURN tên của node (Ví dụ: CẤM chỉ RETURN k.name).
        3. Bạn BẮT BUỘC phải MATCH các node liên kết xung quanh nó và trả về các mối quan hệ.
        
        Câu hỏi: {question}
        Câu lệnh Cypher:"""
    )

    # Prompt trả lời tiếng Việt
    QA_PROMPT = PromptTemplate(
        input_variables=["context", "question"], 
        template="""Bạn là một chuyên gia tư vấn Luật An ninh mạng Việt Nam. 
        Hệ thống đã tự động quét đồ thị và trả về dữ liệu thô ở phần "Thông tin từ Database".
        
        LƯU Ý CỰC KỲ QUAN TRỌNG: 
        1. HÃY TIN TƯỞNG TUYỆT ĐỐI dữ liệu này. Viết lại thành câu trả lời tiếng Việt mạch lạc, dễ hiểu, trình bày dạng gạch đầu dòng.
        2. Nếu dữ liệu thô là rỗng ([]), hãy nói "Tôi không tìm thấy thông tin này trong hệ thống".
        
        Thông tin từ Database:
        {context}
        
        Câu hỏi: {question}
        Câu trả lời (Bằng tiếng Việt):"""
    )

    chain = GraphCypherQAChain.from_llm(
        cypher_llm=llm,          
        qa_llm=llm,              
        graph=graph,             
        verbose=True,            
        qa_prompt=QA_PROMPT,
        cypher_prompt=CYPHER_PROMPT,
        return_intermediate_steps=True,
        allow_dangerous_requests=True  
    )
    return chain

# Khởi tạo chuỗi LangChain
chain = init_graph_chain()

# ==========================================
# 3. XỬ LÝ GIAO DIỆN CHATBOT
# ==========================================
# Lưu trữ lịch sử chat trong Session State
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì cho bạn về Luật An ninh mạng?"}]

# Hiển thị các tin nhắn cũ
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Khung nhập câu hỏi mới
if prompt := st.chat_input("Nhập câu hỏi của bạn (VD: Bộ Công an có trách nhiệm gì?)..."):
    # Hiển thị câu hỏi của người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Hiển thị luồng suy nghĩ của AI
    with st.chat_message("assistant"):
        with st.spinner("AI đang tra cứu mạng đồ thị Neo4j... 🔍"):
            try:
                # Gọi Backend xử lý
                response = chain.invoke({"query": prompt})
                answer = response['result']
                
                # In ra câu trả lời
                st.markdown(answer)
                
                # Lưu vào lịch sử
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # (Tùy chọn) Hiển thị code Cypher ở chế độ gập lại để Demo cho hội đồng
                with st.expander("Xem chi tiết truy vấn Cypher & Data"):
                    st.code(response['intermediate_steps'][0]['query'], language='cypher')
                    st.json(response['intermediate_steps'][1]['context'])
                    
            except Exception as e:
                st.error(f"Xin lỗi, đã xảy ra lỗi trong quá trình xử lý: {str(e)}")