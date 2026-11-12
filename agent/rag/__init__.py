"""Procedure-sheet retrieval (S2-03, FR-AGT-04): sheets -> chunks -> embeddings -> vector store.

The vector store sits behind `store.VectorStore`, so Chroma can be swapped by changing one
file (`store.py`); the final choice is made in Sprint 3 (PL decision #4).
"""
