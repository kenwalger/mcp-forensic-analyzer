# Project Roadmap: Archival Intelligence MCP

This roadmap outlines the planned evolution of the Rare Book Intelligence MCP from a Proof-of-Concept (PoC) to a universal high-value asset authentication engine.

## Phase 1: Core Bibliographic (Current)
- [x] Multi-database relational search (Archive, Catalog, Market).
- [x] Automated status flagging and write-back.
- [x] Permanent forensic audit logging with relational links.
- [x] Evidence-based reporting with auction citations.

## Phase 2: Enhanced Data Integrity (Current)
- [x] **Post 3.2: The Redactor** — PII scrubbing (PERSON, LOCATION, ORGANIZATION) before cloud egress via presidio + spaCy en_core_web_lg. Vision findings scrubbed only when sent to Anthropic/OpenAI; local output unredacted.
- **Global Identifiers:** Integrate **ISBN/OCLC** lookup tools to automatically pull metadata for 20th-century assets, reducing manual entry in the Master Bibliography.
- **Image Analysis (Vision):** Leverage Claude 3.5/3.7 Vision to compare user-uploaded photos of title pages against "Archival Exemplars" stored in Notion.
- **Batch Auditing:** Enable the MCP to scan an entire "New Acquisitions" view in Notion and flag discrepancies across dozens of items in a single pass.

## Phase 3: Vertical Expansion (Future Use Cases)
The underlying "Relational Audit" logic is industry-agnostic. Future "Expert Modules" will include:
- **Numismatics (Coins):** Identifying mint-mark variants and die-clash errors.
- **Philately (Stamps):** Verification of perforations and watermark variations.
- **Sports Memorabilia:** Cross-referencing third-party grading (PSA/BGS) serial numbers with market price API hooks.
- **Luxury Goods:** Forensic stitch-pattern and serial number verification for high-end horology and leather goods.

## Phase 4: Enterprise Features
- **Blockchain Provenance:** Optional "Minting" of an Audit Log to a permanent ledger for high-stakes insurance "Certificates of Authenticity."
- **Multi-Tenant Support:** Enabling different dealers to share a "Common Ground Truth" database while maintaining private Inventory and Market data.

## Phase 5: Production Hardening
- [x] **Judge Framework:** Golden dataset (`tests/golden_dataset.json`) and evaluator (`examples/evaluator.py`) for grading orchestrator output on Precision, Recall, Reasoning Quality.
- [x] **Prompt Externalization:** Prompts moved to `config/prompts.yaml` for easier tuning and versioning.
- [ ] **Stricter Tokenization:** Transition from substring matching to normalized structured tokens for bibliographic verification. `audit_artifact_consistency` marked ready.
- [ ] **Confidence-by-Field:** Implementing weighted scoring where certain fields (like "Typographic Errors") carry more weight than others (like "Binding Color").