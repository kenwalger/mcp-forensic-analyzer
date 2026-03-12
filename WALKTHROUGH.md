# The Forensic Reader’s Journey

This repository is designed as a living reference for the **"End of Glue Code"** series. Because it uses a **Polyglot Architecture** (TypeScript for the MCP Server and Python for the Orchestration), this guide serves as your map to navigating the "Sovereign Vault".

## Path to Enlightenment

Follow the posts in order to see how the system evolves from a simple tool to a hardened forensic architecture.

### 1. The Zero-Glue Foundation

- **The Concept:** Moving from brittle API integrations to standardized tool discovery via the Model Context Protocol (MCP).
- **Key Files:** * `src/index.ts`: The core TypeScript MCP server defining forensic "verbs" (tools) like `audit_book`.
    - `sample_data/rare_books.csv`: Our "Master Bibliography" acting as the ground-truth database.
- **What you learn:** How to expose structured data as MCP Resources and Tools.

### 2. The Local Eye

- **The Concept:** Edge-based Multimodal Vision using Llama 3.2-Vision to process pixels locally.
- **Key Files:**
    - `src/tools/analyze-artifact-vision.ts`: The logic that triggers local inference via Ollama.
    - `examples/orchestrator.py`: The Python agent that receives visual findings and prepares them for the "Airlock."
- **What you learn:** Managing high-latency local AI tasks and implementing a "Zero-Pixel" egress policy.

### 3. The Sovereign Redactor

- **The Concept:** A precision-guided PII airlock that scrubs sensitive data before it hits the cloud.
- **Key Files:**
    - `examples/redactor.py`: The integration with Microsoft Presidio and spaCy.
    - `examples/requirements.txt`: Look for the `# Optional: PII Redactor` section to install dependencies.
- **What you learn:** How to distinguish "Metadata" (Author/Title) from "PII" (Signatures/Locations) using allow-lists.

### 4. The Auditor & The Guardian

- **The Concept:** High-reasoning synthesis and Human-in-the-Loop governance.
- **Key Files:**
    - `examples/orchestrator.py`: Look for the `run_forensic_audit` function and the `Human-in-the-Loop` handshake.
    - `config/prompts.yaml`: The expert persona and reasoning chains for the Auditor.
- **What you learn:** How to implement a "Guardian" pattern that pauses the AI for human authorization on high-severity findings.

### 5. The Judge & The Accountant
 
- **The Concept:** Evaluation frameworks and Cognitive Budgeting.
- **Key Files:**
    - `examples/evaluator.py`: The LLM-as-a-Judge framework for benchmarking accuracy.
    - `examples/router.py`: Semantic routing that sends simple tasks to SLMs and complex ones to Claude.
- **What you learn:** Measuring AI reliability with "Golden Datasets" and optimizing costs through tiered intelligence.


## Design Principles

Regardless of the file, this project adheres to five core principles:

1. **Local-First Processing:** Do the heavy lifting (Vision/Redaction) on your own metal.
2. **Tool-Based Architecture:** Let the Agent discover capabilities; don't hardcode them.
3. **Governance Layers:** Every egress path must pass through an "Airlock".
4. **Cognitive Budgeting:** Use the cheapest model that can solve the problem.
5. **Evaluatable Outputs:** If you can't measure the audit accuracy, it isn't an audit.


**Next Step:** Head to the [Quick Start Guide](README.md) to get your local environment running.