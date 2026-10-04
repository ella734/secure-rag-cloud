# LLMOps & Observability on Azure

## 1. Unified Telemetry Architecture
Operating production Generative AI workloads requires an observability stack capable of tracing non-deterministic LLM behaviors. Azure Monitor and Application Insights provide the foundation for LLMOps telemetry.

## 2. Distributed Tracing with OpenTelemetry
- **Instrumentation**: Standardize on the OpenTelemetry (OTel) Python SDK for vendor-agnostic distributed tracing.
- **Trace Context Propagation**: Every incoming HTTP request must extract or generate a unique correlation ID (`X-Correlation-ID` or W3C `traceparent`), propagated across internal services, vector databases, and external LLM API invocations.
- **Span Decomposition**: A RAG pipeline must segment spans into distinct operational stages:
  1. `rag.input_validation`: Time and outcome of input sanitization and prompt injection checks.
  2. `rag.embedding_generation`: Vectorization latency and token usage.
  3. `rag.vector_retrieval`: Similarity search execution time, similarity scores, and candidate chunk count.
  4. `rag.llm_synthesis`: Time to first token (TTFT), completion generation latency, prompt token count, and completion token count.

## 3. Structured Logging Standards
- All logs must be emitted in structured JSON format to standard output (`stdout`), seamlessly collected by Azure Container Apps log stream and forwarded to Azure Log Analytics workspaces.
- Mandatory log schema attributes include: `timestamp`, `level`, `correlation_id`, `service_name`, `event_type`, `latency_ms`, and `status_code`.
- **Sensitive Data Scrubbing**: Prompts and completions must be sanitized of Personally Identifiable Information (PII) and secret credentials prior to telemetry emission.

## 4. Operational Metrics and Alerting Thresholds
Key service-level indicators (SLIs) for RAG applications:
- **Retrieval Latency**: Median (p50) must remain below 100 ms; p95 must remain below 250 ms.
- **End-to-End Latency**: p95 target of < 2500 ms for standard synthetic responses.
- **Refusal Rate**: Track percentage of queries where the system refuses to answer due to missing knowledge context.
- **Security Block Rate**: Monitor frequency of detected prompt injection attacks, triggering alerts in Microsoft Sentinel if spike exceeds baseline by > 300%.
