# MCP Forensic Analyser
### A Reference Implementation for Protocol-Driven AI Auditing

The **MCP Forensic Analyser** is a Model Context Protocol (MCP) server designed to facilitate deep-dive archival audits and metadata reconciliation. Built as the cornerstone of the [End of Glue Code series](LINK_TO_YOUR_BLOG), it demonstrates how to move from brittle API integrations to a standardized, discovery-based AI architecture.

## 🏛️ Architecture: The "Zero-Glue" Stack
Unlike traditional integrations, this server allows any MCP-compatible agent (Claude, Oracle 26ai, local SLMs) to dynamically discover forensic tools without custom code.



## 🛠️ Features
- **Discovery-First:** Implements the full MCP Lifecycle (Handshake -> Manifest -> Execution).
- **Archival Tools:** Specialized functions for metadata cross-referencing and watermark verification.
- **Polyglot Ready:** Built in TypeScript, designed to be orchestrated by Python-based agentic frameworks.

## 🚀 Quick Start

### Installation
```bash
npm install
npm run build
```

## 🏠 Edge AI: Running Locally with SLMs
This branch demonstrates the "Forensic Clean-Room" setup, moving inference from the cloud to your local machine.

### Prerequisites
1. **Ollama:** [Download and install Ollama](https://ollama.com/).
2. **Model:** Pull the default model (or another of your choice):
   ```bash
   ollama pull llama3.2
   ```
   The orchestrator defaults to `llama3.2`; for other models (e.g. phi4), set `LLM_MODEL` (see below).

### Running the Local Orchestrator
To run the multi-agent team using the local SLM:

```bash
python examples/orchestrator.py --provider ollama
```

To use a different model, set the `LLM_MODEL` environment variable:
```bash
LLM_MODEL=phi4 python examples/orchestrator.py --provider ollama
```

> Note: SLMs require explicit instruction tuning. The orchestrator includes an optimized system prompt to help small models handle MCP JSON schemas effectively.
