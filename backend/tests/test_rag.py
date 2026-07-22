import sys
sys.path.insert(0, '../')

from services.rag_service import retrieve_context, get_corpus_stats

def test_rag_retrieval_returns_context():
    context, latency = retrieve_context("conjunction risk LEO debris", top_k=2)
    assert len(context) > 0
    assert "NASA" in context or "ESA" in context or "JSC" in context
    assert latency < 50

def test_rag_corpus_stats():
    stats = get_corpus_stats()
    assert stats["documents"] == 5
    assert "sentence-transformers" in stats["embedding_model"]
