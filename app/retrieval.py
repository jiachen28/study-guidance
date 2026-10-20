"""Dependency-free TF–IDF retrieval over a small, attributed knowledge base."""
from collections import Counter
from functools import lru_cache
import json
import math
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
_TOKEN = re.compile('(?u)\\b[^\\W_]+\\b')

def tokens(text):
    return _TOKEN.findall(text.lower())

@lru_cache(maxsize=1)
def references():
    rows = json.loads((ROOT / 'data' / 'knowledge.json').read_text(encoding='utf-8'))
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate reference IDs')
    return rows

@lru_cache(maxsize=1)
def _index():
    docs = [Counter(tokens(' '.join([r['note'], r['keywords'], r['category'], r['topic']]))) for r in references()]
    n = len(docs)
    df = Counter((term for doc in docs for term in doc))
    idf = {word: math.log((1 + n) / (1 + freq)) + 1 for word, freq in df.items()}

    def normed(doc):
        values = {word: (1 + math.log(freq)) * idf[word] for word, freq in doc.items()}
        norm = math.sqrt(sum((v * v for v in values.values()))) or 1
        return {word: v / norm for word, v in values.items()}
    return ([normed(d) for d in docs], idf)

def retrieve(task, *, category=None, limit=4):
    """Returns only meaningful matches; never treats an unknown query as evidence."""
    vectors, idf = _index()
    query = Counter((t for t in tokens(task) if t in idf))
    q = {t: (1 + math.log(n)) * idf[t] for t, n in query.items()}
    norm = math.sqrt(sum((v * v for v in q.values()))) or 1
    q = {t: v / norm for t, v in q.items()}
    ranked = []
    for row, vector in zip(references(), vectors):
        similarity = sum((value * vector.get(t, 0) for t, value in q.items()))
        if category and row['category'] not in ('General', category):
            similarity *= 0.35
        if similarity > 0:
            ranked.append((similarity, row['id'], row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [dict(row, similarity=round(score, 3)) for score, _, row in ranked[:limit]]
