from operator import itemgetter
import os
import pandas as pd
import numpy as np

from dotenv import load_dotenv
load_dotenv()

# Import các thư viện LangChain & Google
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings # dùng local embedding cho đỡ tốn token
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
# bản chains đã cũ không dùng được nữa
# from langchain.chains.combine_documents import create_stuff_documents_chain
# from langchain.chains import create_retrieval_chain

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# --- 1. CẤU HÌNH API KEY ---
# Bạn có thể set cứng hoặc nhập khi chạy (an toàn hơn)
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")



# --- 2. XỬ LÝ DỮ LIỆU THÔNG MINH (GROUPING) ---
# Bước này không cần nữa
# print("📊 Đang load và gộp dữ liệu...")
# try:
#     df = pd.read_csv("./Scrape/DoAn_HUST_Chrome.csv")
#     df['GiangVien'] = df['GiangVien'].replace(r'^\s*$', np.nan, regex=True).ffill()
#     df['GiangVien'] = df['GiangVien'].replace('nan', np.nan, regex=True).ffill()
#     df = df.fillna("Không có thông tin")
    
#     # --- THAY ĐỔI LỚN: GỘP THEO GIẢNG VIÊN ---
#     # Thay vì 482 documents, ta gộp lại chỉ còn khoảng 50-60 documents (1 doc = 1 Giảng viên)
#     documents = []
    
#     # Nhóm các dòng theo tên Giảng viên
#     grouped = df.groupby('GiangVien')
    
#     for teacher_name, group in grouped:
#         # Tạo danh sách đề tài của giảng viên này
#         topics_list_str = ""
#         for idx, row in group.iterrows():
#             topics_list_str += f"- [Đề tài: {row['TenDeTai']}]: {row['ChiTiet']}\n"
        
#         # Tạo nội dung Document (List to)
#         content = f"""
#         THÔNG TIN GIẢNG VIÊN
#         Họ và tên: {teacher_name}
        
#         DANH SÁCH CÁC ĐỀ TÀI HƯỚNG DẪN:
#         {topics_list_str}
#         """.strip()
        
#         # Metadata vẫn giữ tên giảng viên để filter nếu cần
#         metadata = {
#             "teacher": str(teacher_name),
#             "topic_count": len(group) # Lưu thêm số lượng đề tài
#         }
        
#         documents.append(Document(page_content=content, metadata=metadata))
        
#     print(f"✅ Đã gộp 482 dòng thành {len(documents)} văn bản (mỗi văn bản là 1 giảng viên).")

# except Exception as e:
#     print(f"❌ Lỗi load file: {e}")
#     documents = []
    

# --- 3. KHỞI TẠO HuggingFaceEmbeddings EMBEDDING & VECTOR DB ---
print("🛠️ Đang khởi tạo Embedding và Vector DB...")
embedding_model = HuggingFaceEmbeddings(model_name="keepitreal/vietnamese-sbert")
# embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

persist_dir = "./chroma_db_huggingface"

# Kiểm tra xem DB đã tồn tại chưa để tránh embed lại tốn thời gian
if os.path.exists(persist_dir):
    print("🔄 Đã tìm thấy Vector DB cũ, đang tải lên...")
    vector_db = Chroma(persist_directory=persist_dir, embedding_function=embedding_model)
else:
    print("🚀 Đang tạo Vector DB mới (local Huggingface để embed)...")
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=persist_dir
    )
    print("✅ Đã tạo xong Vector DB!")

# --- 4. KHỞI TẠO LLM (GEMINI 1.5 FLASH) ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0, # 0 để trả lời chính xác, ít "chém gió"
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# --- 5. TẠO RAG CHAIN ---
# Prompt template
# 1. Định nghĩa Template thống nhất tên biến là {input} và {context}
template = """Bạn là trợ lý tư vấn chọn đề tài đồ án.
Dựa vào ngữ cảnh (danh sách đề tài) dưới đây để trả lời câu hỏi.

Quy tắc:
- Nếu không tìm thấy thông tin, hãy nói "Tôi không tìm thấy thông tin trong dữ liệu được cung cấp".
- Chỉ trả lời dựa trên ngữ cảnh.

Ngữ cảnh:
{context}

Câu hỏi:
{input}

Trả lời:"""

# prompt = ChatPromptTemplate.from_messages([
#     ("system", template)
# ])
prompt = ChatPromptTemplate.from_template(template)
# Hàm format các văn bản tìm được thành 1 chuỗi string duy nhất để ném vào Prompt
def format_docs(docs):
    return "\n\n" + "="*20 + "\n\n".join(doc.page_content for doc in docs)
# Tạo Chain
retriever = vector_db.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 59} # Lấy toàn bộ kết quả, vì nếu lấy ít hơn thì nó rất ngẫu nhiên ra các thầy cô 
)


# Định nghĩa Chain xử lý input dạng Dictionary {"input": "..."}
# Sử dụng itemgetter('input') để lấy giá trị câu hỏi từ dict
rag_chain = (
    {
        "context": itemgetter("input") | retriever | format_docs,
        "input": itemgetter("input")
    }
    | prompt
    | llm
    | StrOutputParser()
)

# --- 6. CHẠY THỬ (ĐÃ FIX CÁCH GỌI VÀ IN) ---
print("\n✅ Hệ thống sẵn sàng! (Gõ 'exit' để thoát)")

while True:
    query = input("\n🔍 Hỏi: ")
    if query.lower() in ["exit", "quit"]:
        break
    
    try:
        print("⏳ Gemini đang suy nghĩ...")
        
        # 1. Gọi invoke với Dictionary
        response = rag_chain.invoke({"input": query})
        
        # 2. In kết quả (Lưu ý: response bây giờ là String, không phải Dict)
        print("\n🤖 GEMINI TRẢ LỜI:")
        print(response) # <-- Sửa lỗi: In trực tiếp, không dùng ["answer"]
        
    except Exception as e:
        print(f"❌ Lỗi chi tiết: {e}")
        # (Tuỳ chọn) Xem nó đã lấy thông tin từ đề tài nào
        # print("\n[Nguồn tham khảo]:")
        # for doc in response["context"]:
        #     print(f"- {doc.page_content.splitlines()[0]}")
            