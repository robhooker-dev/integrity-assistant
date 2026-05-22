import os
import pickle
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOCS_DIR = Path(__file__).parent.parent / "data" / "documents"
STORE_PATH = Path(__file__).parent.parent / "vectorstore" / "tfidf_store.pkl"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def chunk_text(text: str, source: str) -> list[dict]:
    words = text.split()
    step = CHUNK_SIZE - CHUNK_OVERLAP
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        if len(chunk.strip()) > 50:
            chunks.append({"text": chunk, "source": source, "chunk_index": len(chunks)})
    return chunks


def load_documents() -> list[dict]:
    all_chunks = []
    for filepath in DOCS_DIR.iterdir():
        if filepath.suffix == ".txt":
            text = filepath.read_text(encoding="utf-8")
            chunks = chunk_text(text, filepath.name)
            all_chunks.extend(chunks)
            print(f"  Loaded {filepath.name}: {len(chunks)} chunks")
        elif filepath.suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(filepath))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                chunks = chunk_text(text, filepath.name)
                all_chunks.extend(chunks)
                print(f"  Loaded {filepath.name}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  Failed {filepath.name}: {e}")
    return all_chunks


def build_index(force_rebuild: bool = False) -> dict:
    STORE_PATH.parent.mkdir(exist_ok=True)
    
    if STORE_PATH.exists() and not force_rebuild:
        with open(STORE_PATH, "rb") as f:
            store = pickle.load(f)
        print(f"Loaded existing index ({len(store['chunks'])} chunks)")
        return store
    
    print("Building index from documents...")
    chunks = load_documents()
    if not chunks:
        raise ValueError("No documents found in data/documents/")
    
    texts = [c["text"] for c in chunks]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    
    store = {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}
    with open(STORE_PATH, "wb") as f:
        pickle.dump(store, f)
    
    print(f"Index built: {len(chunks)} chunks")
    return store


def query_index(store: dict, query: str, n: int = 5) -> list[dict]:
    vec = store["vectorizer"].transform([query])
    scores = cosine_similarity(vec, store["matrix"]).flatten()
    top_indices = np.argsort(scores)[::-1][:n]
    results = []
    for i in top_indices:
        if scores[i] > 0:
            results.append({**store["chunks"][i], "score": float(scores[i])})
    return results


def get_index():
    return build_index()
