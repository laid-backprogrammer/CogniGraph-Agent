# storage/vector_store.py
"""
向量存储实现 - ChromaDB
"""

import json
from typing import Dict, List, Any, Optional
import chromadb
from openai import OpenAI

from config import get_settings
from .base import BaseVectorStorage


class EmbeddingService:
    """嵌入向量服务"""

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.embedding_model
        self._cache: Dict[str, List[float]] = {}

    def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        if text in self._cache:
            return self._cache[text]

        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            embedding = response.data[0].embedding
            self._cache[text] = embedding
            return embedding
        except Exception as e:
            print(f"⚠️ Embedding 失败: {e}")
            return [0.0] * 1536

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        results = []
        uncached = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if text in self._cache:
                results.append(self._cache[text])
            else:
                results.append(None)
                uncached.append(text)
                uncached_indices.append(i)

        if uncached:
            try:
                response = self.client.embeddings.create(
                    input=uncached,
                    model=self.model
                )
                for i, data in enumerate(response.data):
                    idx = uncached_indices[i]
                    results[idx] = data.embedding
                    self._cache[uncached[i]] = data.embedding
            except Exception as e:
                print(f"⚠️ Batch embedding 失败: {e}")
                for idx in uncached_indices:
                    results[idx] = [0.0] * 1536

        return results


class ChromaVectorStore(BaseVectorStorage):
    """ChromaDB 向量存储"""

    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="knowledge_nodes",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_service = EmbeddingService()

    def add(self, id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """添加或更新向量"""
        metadata = metadata or {}
        embedding = self.embedding_service.embed(text)

        try:
            self.collection.upsert(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )
            return True
        except Exception as e:
            print(f"⚠️ 向量存储失败: {e}")
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            print(f"🔍 向量搜索: {query}")
            query_embedding = self.embedding_service.embed(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["metadatas", "distances", "documents"]
            )

            items = []
            if results['ids'] and results['ids'][0]:
                for i, id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    document = results['documents'][0][i] if results['documents'] else ""

                    items.append({
                        "id": id,
                        "similarity": 1 - distance,
                        "metadata": metadata,
                        "document": document
                    })
            print(f"🔍 向量搜索结果: {json.dumps(items, ensure_ascii=False)}")
            return items
        except Exception as e:
            print(f"⚠️ 向量搜索失败: {e}")
            return []

    def delete(self, id: str) -> bool:
        """删除向量"""
        try:
            self.collection.delete(ids=[id])
            return True
        except Exception:
            return False

    def clear(self) -> bool:
        """清空所有向量"""
        try:
            self.collection.delete(where={})
            return True
        except Exception:
            return False
