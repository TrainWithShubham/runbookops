# How RunbookOps works

```mermaid
flowchart TD
    U[Authenticated user or local development identity] --> G[LangGraph investigation]
    G --> M[Explicit model provider]
    G --> C[MCP client]
    C --> T[Bounded tools]
    T --> R[Chroma retrieval with access filters]
    T --> S[Checkout simulator state]
    G --> P[Validated proposal]
    P --> H[Persistent human approval checkpoint]
    J[Jethalal with approve scope] --> H
    H --> E[Application executor]
    E --> V[Health verification]
```

The model chooses permitted read and proposal tools. The application validates the tool name and arguments and binds calls to a trusted user and incident. Four operational/document checks are required before a proposal can be prepared.

The model has no apply tool. The graph pauses on the stored proposal; a separate authorized decision updates its status. The executor checks the approved hash and current service state, applies one allowlisted simulator change, and verifies the resulting health.

Knowledge documents are extracted into source-located sections, chunked, embedded, and stored in Chroma. Metadata marks source identity, version, freshness, and access. The query filters run before any result enters model context. Both a fully offline lexical hash mode and a small downloaded semantic embedding model are available and labeled.

Local state uses SQLite for operations and a separate SQLite LangGraph checkpointer. The instructor deployment uses a DynamoDB incident aggregate and the maintained DynamoDB LangGraph saver. DynamoDB uses conditional writes for approval and simulator changes. PostgreSQL adapters remain optional but are not the deployed workshop route.

AgentCore Runtime hosts this code. Its managed Harness is a separate alternative orchestration loop powered by Strands. The cloud demo uses Bedrock inference; learner applications use individual OpenRouter keys. The instructor's credits and credentials are never distributed to learners.

The simulator represents a payment dependency through state and log fixtures. It does not make a real payment request. That keeps failure injection repeatable while teaching the evidence, authorization, and recovery boundaries.

## Presenter backend

`runbookops present` serves the browser locally and forwards an allowlisted HTTP envelope to the runtime through the AWS SDK. Its static shell and demo issuer are local; its harness inspection, RAG, MCP discovery, incident state, and proposal decisions come from the cloud agent. A separate streaming operation wraps the shared event generator in SSE for AgentCore; the local bridge translates it back to the UI's NDJSON contract. The bridge creates no duplicate local agent or retrieval index.

IAM authenticates invocation. A scoped demo JWT is added before signing using a per-call context variable, preventing concurrent requests from mixing identities. The runtime validates the forwarded token and applies its normal route authorization/schema checks. Investigation and decision invocations use fresh session IDs; DynamoDB rather than process memory preserves approval state across them. Read-only inspection and RAG searches reuse a serialized, per-identity/scopes session to preserve the warm retrieval cache without mixing callers.

The local presenter has persistent per-runtime daily admission and one active investigation. These limits do not govern a separate IAM client invoking the runtime directly. Model/tool budgets are still enforced inside the engine. See [AWS deployment](AWS.md) and [cost limits](COSTS.md).
