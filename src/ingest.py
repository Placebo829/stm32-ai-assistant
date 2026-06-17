import os
import time
import json
import numpy as np
import faiss
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"]
)

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vector_store"))
os.makedirs(OUTPUT_PATH, exist_ok=True)

TEXTS_PATH = os.path.join(OUTPUT_PATH, "texts.json")
VECTORS_PATH = os.path.join(OUTPUT_PATH, "vectors_partial.json")
INDEX_PATH = os.path.join(OUTPUT_PATH, "index.faiss")

# ── 載入 PDF ──────────────────────────────────────────────
all_docs = []
print("🚀 Loading PDFs...")
for root, dirs, files in os.walk(DATA_PATH):
    for f in files:
        if f.endswith(".pdf"):
            loader = PyMuPDFLoader(os.path.join(root, f))
            all_docs.extend(loader.load())
print(f"✔ Loaded {len(all_docs)} pages")

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(all_docs)
print(f"✔ chunks: {len(chunks)}")

texts = [c.page_content for c in chunks[:2000]]

# 儲存完整 texts（只存一次）
if not os.path.exists(TEXTS_PATH):
    with open(TEXTS_PATH, "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)
    print("✔ texts.json saved")

# ── 讀取已有進度 ──────────────────────────────────────────
if os.path.exists(VECTORS_PATH):
    with open(VECTORS_PATH, "r") as f:
        done_vectors = json.load(f)
    start_idx = len(done_vectors)
    print(f"🔄 Resuming from {start_idx}/{len(texts)}")
else:
    done_vectors = []
    start_idx = 0
    print("🆕 Starting fresh")


# ── Embedding ─────────────────────────────────────────────
def embed_batch(batch):
    while True:
        try:
            res = client.embeddings.create(
                model="nvidia/nv-embedqa-e5-v5",
                input=batch,
                encoding_format="float",
                extra_body={"input_type": "passage", "truncate": "END"}
            )
            return [e.embedding for e in res.data]
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                print(f"  ⚠ Rate limit hit, waiting 30s...")
                time.sleep(30)
            else:
                raise


BATCH_SIZE = 50
print("🔥 Embedding...")

for i in range(start_idx, len(texts), BATCH_SIZE):
    batch = texts[i:i + BATCH_SIZE]
    vectors = embed_batch(batch)
    done_vectors.extend(vectors)

    # 每批存一次進度
    with open(VECTORS_PATH, "w") as f:
        json.dump(done_vectors, f)

    print(f"  Embedded & saved {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    time.sleep(0.5)

# ── 建 FAISS index ────────────────────────────────────────
print("⚙ Building FAISS index...")
vectors_np = np.array(done_vectors).astype("float32")
dim = vectors_np.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(vectors_np)
faiss.write_index(index, INDEX_PATH)

print("✔ Vector DB built & saved to vector_store/")
print(f"  Total vectors: {len(done_vectors)}")