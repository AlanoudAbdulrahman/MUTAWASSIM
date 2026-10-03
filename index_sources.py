import json
import chromadb
from chromadb.utils import embedding_functions

def build_index(docs_path="sources.json", persist_directory="./chroma_db"):
    """
    يبني فهرس Chroma من ملف المصادر الموحد باستخدام نماذج SentenceTransformers (sbert.net).
    """
    print(f"Reading sources from {docs_path}...")
    try:
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {docs_path}. Please ensure it exists.")
        return
        
    # تهيئة عميل Chroma في مسار محلي
    client = chromadb.PersistentClient(path=persist_directory)
    
    # استخدام نموذج متعدد اللغات كما هو محدد في الخطة (paraphrase-multilingual)
    # يمكن تغييره إلى intfloat/multilingual-e5-base إذا تطلب الأمر
    print("Loading embedding model (paraphrase-multilingual-MiniLM-L12-v2)...")
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    # إنشاء أو جلب المجموعة (Collection)
    collection = client.get_or_create_collection(
        name="mutawassim_sources", 
        embedding_function=sentence_transformer_ef
    )
    
    ids = []
    documents = []
    metadatas = []
    
    for doc in docs:
        ids.append(doc["id"])
        documents.append(doc["text"])
        metadatas.append({
            "url": doc["url"],
            "ruling": doc["ruling"],
            "source": doc["source"],
            "type": doc["type"]
        })
        
    print(f"Adding {len(docs)} documents to the index...")
    # إضافة الوثائق إلى الفهرس
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("Index built successfully! The data is saved in", persist_directory)

if __name__ == "__main__":
    build_index()
