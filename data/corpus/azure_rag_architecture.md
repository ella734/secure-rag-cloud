# Production RAG Architecture and Anti-Hallucination Design

## 1. Chunking and Preprocessing Strategies
- **Hierarchical Chunking**: Documents are split into semantic units balancing granular context preservation with retrieval efficiency. Chunk sizes between 300 to 800 tokens with 10% to 20% overlap prevent sentence splitting and information fragmentation.
- **Metadata Enrichment**: Each document chunk preserves structural metadata: `document_title`, `section_heading`, `source_filename`, and `chunk_index`. This allows downstream citations and metadata-driven pre-filtering.

## 2. Dense Vector Retrieval and Similarity Metrics
- Vector embeddings capture high-dimensional conceptual meanings. Cosine similarity calculates angular distance between query vectors and stored chunk vectors:
  $$\text{Cosine Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$$
- **Relevance Thresholding**: Chunks with similarity score below the minimum threshold (e.g. 0.20) are excluded to prevent contaminating the generation prompt with irrelevant background noise.
- **Top-K Selection**: Selecting between 3 to 5 candidate chunks delivers sufficient factual evidence without overflowing the LLM attention window.

## 3. Strict Refusal and Grounding Strategy
- **Grounding Mandate**: The generation engine must be instructed via system prompts to answer strictly and exclusively based on the provided context passages.
- **Refusal Mechanism**: When retrieved passages do not contain explicit, verifiable facts answering the user query, the LLM must explicitly refuse to fabricate an answer:
  > *"Je ne dispose pas d'informations suffisantes dans la documentation fournie pour répondre à cette question."*
- Fabricating plausible-sounding technical information is treated as a critical failure (hallucination).

## 4. Citation and Traceability
- Every factual assertion generated in the final answer must cite its corresponding source chunk using inline brackets (e.g. `[Doc 1]`, `[Doc 2]`).
- Citations enhance user trust, enable instant human auditing, and satisfy regulatory explainability requirements under the EU AI Act.
