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