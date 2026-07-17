"""
Pure Python BM25 Searcher for keyword matching
"""
import math
from typing import List, Dict, Any, Tuple

class BM25:
    """Pure Python BM25 Searcher for keyword matching"""
    def __init__(self, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_lens = []
        
        for item in corpus:
            text = f"{item.get('description', '')} {item.get('location', '')} {' '.join(item.get('objects', []))} {item.get('activity_type', '')}"
            words = [w.lower().strip(",.?!()\"'") for w in text.split() if w]
            self.documents.append(words)
            self.doc_lens.append(len(words))
            
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0
        self.doc_count = len(corpus)
        
        self.df = {}
        for doc in self.documents:
            unique_words = set(doc)
            for word in unique_words:
                self.df[word] = self.df.get(word, 0) + 1
                
        self.idf = {}
        for word, freq in self.df.items():
            self.idf[word] = math.log((self.doc_count - freq + 0.5) / (freq + 0.5) + 1.0)

    def score(self, query: str) -> List[Tuple[float, Dict[str, Any]]]:
        query_words = [w.lower().strip(",.?!()\"'") for w in query.split() if w]
        scores = []
        
        for idx, doc in enumerate(self.documents):
            score = 0.0
            doc_len = self.doc_lens[idx]
            word_counts = {}
            for w in doc:
                word_counts[w] = word_counts.get(w, 0) + 1
                
            for qw in query_words:
                if qw in word_counts:
                    tf = word_counts[qw]
                    idf_val = self.idf.get(qw, 0.0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                    score += idf_val * (numerator / denominator)
            scores.append((score, self.corpus[idx]))
            
        return scores
