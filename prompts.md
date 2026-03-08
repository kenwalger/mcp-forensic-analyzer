# 📋 Forensic Test Suite & Prompts

Use these prompts in Claude Desktop to verify the relational logic and forensic auditing capabilities of the Rare Book Intelligence MCP.

### ⚠️ Setup Note: 
For these prompts to work end-to-end, ensure the book titles in your Notion databases match the prompt text exactly (e.g., use a straight apostrophe in Alice's).

## 🛠️ Global Audit Protocol
This is the master prompt used to trigger the multi-database forensic chain (Search -> Archive -> Market -> Audit -> Log).

###  Expected Outcome: 
Claude should identify the discrepancy, update the Catalog status to 'Flagged', and create a linked record in the Audit History with the full forensic report.

## 💡 Quick Start for Judges: 
To see the full forensic chain in under 60 seconds, copy and paste the Gatsby Audit prompt. It demonstrates cross-database lookups, market price risk analysis, and automated status flagging in Notion.

## 📙 The Great Gatsby (1925)
**Forensic Focus:** The lowercase "j" in "jay gatsby" on the back of the dust jacket.

**Prompt:**

I am conducting a formal forensic audit on The Great Gatsby. Please follow this protocol:

1. Search Catalog: Find the entry for 'The Great Gatsby' in the Books Catalog.

2. Archival Lookup: Search the 'Master Bibliography' for 'The Great Gatsby' (1925) to retrieve the 'Ground Truth' for the dust jacket states.

3. Market Analysis: Query 'Market Results' for the price difference between a 1st state jacket (lowercase 'j') and a 2nd state jacket (capital 'J').

4. Forensic Collation: Compare the observation (Back jacket has a capital 'J' in 'Jay Gatsby') against the Master Bibliography requirement (must be lowercase 'j').

5. Execution: >    - If the discrepancy is confirmed, update the Catalog Status to 'Flagged'.

+ Create a new entry in the Audit Log database detailing the overvaluation risk ($100k+ discrepancy).

6. Reporting: Provide the final Exhibit Label in Markdown and confirm the Notion Page IDs you updated.

7. Citation: If applicable, include the citation link from the Market Results in your final report.

## Alice's Adventures in Wonderland
**Forensic Focus:** The "wabe" vs. "wade" textual variant in the Jabberwocky poem (page 192). This identifies the 1866 first trade edition state versus later, less valuable reprints.

**Prompt:**

I am conducting a formal forensic audit on a high-value asset. Please follow this exact protocol using the rare-book-expert tools:

1. Search Catalog: Find the entry for 'Alice's Adventures in Wonderland' in the Books Catalog.

2. Archival Lookup: Search the 'Master Bibliography' for the same title to retrieve the 'Ground Truth' for the 1866 edition.

3. Market Analysis: Query 'Market Results' for any valuation data on this title.

4. Forensic Collation: Compare my observation (Page 192 reads 'wade') against the Master Bibliography requirement (must read 'wabe').

5. Execution: >    - If the 'wade' discrepancy is confirmed as a 2nd-state or reprint marker, update the Catalog Status to 'Flagged'.

  + Create a new entry in the Audit Log database. Include the Book Title, the Result ('Fail/Discrepancy'), and a summary of the $50,000+ value risk.

6. Reporting: Provide the final Exhibit Label in Markdown and confirm the Notion Page IDs you updated.

7. Citation: If applicable, include the citation link from the Market Results in your final report.

## 📘 The Hobbit (1937)
**Forensic Focus:** The "Dodgeson" typo on the back flap and the "First Printing" copyright statement.

**Prompt:**

I am conducting a formal forensic audit on a copy of The Hobbit. Please follow this protocol:

1. Search Catalog: Find the entry for 'The Hobbit' in the Books Catalog.

2. Archival Lookup: Search the 'Master Bibliography' for 'The Hobbit' by J.R.R. Tolkien to retrieve the 1937 First Impression requirements.

3. Market Analysis: Query 'Market Results' for any valuation data on 1st/1st copies vs. later impressions.

4. Forensic Collation: Compare the observation (Back flap typo reads 'Dodgeson' with an extra 'e') against the archival standard.

5. Execution: >    - If the 'Dodgeson' typo is present (confirming a true 1st impression), update the Catalog Status to 'Pass'.

  + If the typo is missing (indicating a later printing), update the Status to 'Flagged'.

  + Create a new entry in the Audit Log database including the result and the market value context.

6. Reporting: Provide the final Exhibit Label and confirm the Notion IDs updated.

7. Citation: If applicable, include the citation link from the Market Results in your final report.

---

## 💡 Pro-Tip for Judges

When running these prompts, observe the **Tool Use** window in Claude. You will see the agent orchestrating 4-5 distinct database calls to formulate its expert opinion.

### Success Metric
A successful run should conclude with two distinct green tool-call bubbles in Claude for `update_book_status` and `create_audit_log`, resulting in a clickable link between your Notion databases.