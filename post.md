---
title: Archival Intelligence: A Forensic Rare Book Auditor
published: false
tags: devchallenge, notionchallenge, mcp, ai
---

## 🔍 Archival Intelligence: A Forensic Rare Book Auditor

*This is a submission for the [Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04)*

## What I Built
I built the **Rare Book Intelligence MCP Server**, a specialized forensic agent that turns a Notion workspace into an expert appraisal lab. In the world of high-value assets, the difference between a lowercase 'j' and a capital 'J' on a 1925 *Gatsby* dust jacket represents a **$150,000 valuation swing**. 

This MCP server enables AI agents (like Claude) to navigate a relational graph of four distinct Notion databases—**Inventory, Master Bibliography, Market Results, and Audit History**—to identify forgeries, verify states, and automate the "Chain of Custody" for rare artifacts.

## Video Demo
{% youtube -cdzvxks5MI %}
*[Archival Intelligence: Solving $150k Rare Book Forgeries with Notion & MCP](https://www.youtube.com/watch?v=-cdzvxks5MI)*

## Show us the code
Find the full source code, test suite, and prompt library here:
[GitHub Repository: kenwalger/Notion_MCP_Challenge_2026](https://github.com/kenwalger/Notion_MCP_Challenge_2026)

## How I Used Notion MCP
Most MCP implementations focus on simple data retrieval. I pushed the **Model Context Protocol** further by creating a **Relational Write-Back Loop**:

1.  **Forensic Search:** The agent queries the *Books Catalog* for observed data.
2.  **Archival Collation:** It retrieves "Ground Truth" standards from a private *Master Bibliography*.
3.  **Market Intelligence:** It analyzes historical sales in the *Market Results* database.
4.  **Automated Governance:** If a discrepancy is found (like the "j" variant in *The Great Gatsby*, or the 'wabe/wade' variant in *Alice's Adventures in Wonderland'), the agent uses the Notion API to:
    * Flip the inventory status to **"Flagged"**.
    * Create a permanent, timestamped **Audit Log**.
    * **Relational Linking:** Automatically link the log entry back to the catalog item, ensuring a verifiable provenance record.
    * **Automated Export:** Generate a museum-read **Exhibit Label** in Markdown, synthesizing complex forensic findings into a clear, actionable summary for curators.

This unlocks a forensic "expert-in-your-pocket" workflow for any dealer, collector, or insurance adjuster using Notion.

## Reflections & Future Scaling
This project proves that the Model Context Protocol can do more than summarize text—it can enforce **Technical Governance**. While we used Rare Books as our proof-of-concept, the relational logic is built for the entire multi-billion dollar collectibles market.

At **Abiqua Archive**, we are scaling this logic to help museums and private collectors automate trust and protect the "Iron and Ink" of our shared history.

---
**Ken W. Alger**