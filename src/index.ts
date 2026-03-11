#!/usr/bin/env node
/**
 * Rare Books Intelligence MCP Server
 * Orchestrates forensic bibliographic audits by connecting
 * Notion databases with LLM reasoning capabilities.
 * @author Ken W. Alger (Abiqua Archive)
 * @version 0.14.0
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { 
    executeSearchBooks, 
    executeAuditArtifactConsistency, 
    executeGenerateExhibitLabel, 
    executeGetMarketSignals, 
    executeFindBookInMasterBibliography,
    executeUpdateBookStatus,
    executeCreateAuditLog,
    executeRequestHumanSignature,
    executeAnalyzeArtifactVision,
} from "./tools/index.js";
import { BookStandardSchema } from "./lib/schemas.js";

const FORENSIC_WORKFLOW_INSTRUCTIONS = `
## Forensic Workflow
1. find_book_in_master_bibliography
2. analyze_artifact_vision – (Sovereign Vault) When an artifact image is available, analyze it locally first. NEVER route to cloud; local Ollama only.
3. audit_artifact_consistency
4. request_human_signature – For any HIGH severity finding, you MUST request human authorization before finalizing. You are a Co-Pilot; do not act autonomously on high-stakes accusations.
5. get_market_signals – When reporting market findings, always include the citation link or reference provided in the Market Results to ensure evidence-based auditing.
6. generate_exhibit_label – Once an audit is successful, offer to generate a formal Exhibit Label. If the user agrees, use the generate_exhibit_label tool and suggest saving the output back to the Notion page's 'Full Report' field.
7. update_book_status – Only when a High severity discrepancy has been explicitly authorized by the human (per step 4). Do not flag findings that were disputed or rejected; disputed findings belong in "Requires Further Investigation" instead. If the human has not yet approved, wait for approval before calling update_book_status.
8. create_audit_log – After an audit is complete, automatically call create_audit_log to maintain a permanent record. You MUST pass the id from the Catalog search result into the catalog_page_id parameter of create_audit_log to maintain the relational thread.
`;

const server = new McpServer({
    name: "rare-books-intelligence-mcp",
    version: "0.14.0",
}, {
    capabilities: { tools: {} },
    instructions: FORENSIC_WORKFLOW_INSTRUCTIONS.trim(),
});

// --- TOOL REGISTRATION START ---
// Note: registerTool(name, { description, inputSchema }, handler)

server.registerTool(
    "search_books",
    {
        description: "Search the rare books database in Notion.",
        inputSchema: {
            query: z.string().optional(),
            author: z.string().optional(),
            minYear: z.number().optional(),
            maxYear: z.number().optional(),
            condition: z.enum(["mint", "fine", "very_good", "good", "fair", "poor"]).optional(),
        }
    },
    async (args: any) => {
        const result = await executeSearchBooks(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    }
);

server.registerTool(
    "audit_artifact_consistency",
    {
        description: "Compare physical observations against Ground Truth.",
        inputSchema: {
            book_standard_page_id: z.string().optional(),
            book_standard: BookStandardSchema.optional().describe("Inline BookStandard when Notion lookup unavailable"),
            observed: z.object({
                first_edition_indicators_observed: z.array(z.string()),
                points_of_issue_observed: z.array(z.string()),
                observed_year: z.number().optional(),
                binding_type_observed: z.string().optional(),
                paper_watermark_observed: z.string().optional(),
            }),
            market_context: z.string().optional(),
            vision_context: z.string().optional().describe("Visual analysis from analyze_artifact_vision (Sovereign Vault)"),
        }
    },
    async (args: any) => {
        const result = await executeAuditArtifactConsistency(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    }
);

server.registerTool(
    "find_book_in_master_bibliography",
    {
        description: "Look up a book in the Master Bibliography.",
        inputSchema: {
            title: z.string(),
            author: z.string().optional(),
        }
    },
    async (args: any) => {
        const result = await executeFindBookInMasterBibliography(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    }
);

server.registerTool(
    "get_market_signals",
    {
        description: "Query market results for valuation.",
        inputSchema: {
            title: z.string(),
            author: z.string().optional(),
        }
    },
    async (args: any) => {
        const result = await executeGetMarketSignals(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    }
);

server.registerTool(
    "generate_exhibit_label",
    {
        description: "Generate a high-fidelity Markdown exhibit placard for museum display. Returns formatted sections: Archival Description, Forensic Verification Summary, Valuation Context, plus disclaimer.",
        inputSchema: {
            book_data: z.record(z.unknown()).describe("Book metadata (title, author, publisher, year, binding, etc.) from Master Bibliography or catalog"),
            audit_results: z.record(z.unknown()).describe("Audit findings from audit_artifact_consistency (result, confidence, discrepancies)"),
            market_citation: z.string().describe("Citation link or reference from Market Results for valuation evidence"),
        }
    },
    async (args: any) => {
        const result = executeGenerateExhibitLabel(args);
        return { content: [{ type: "text", text: result }] };
    }
);

server.registerTool(
    "update_book_status",
    {
        description: "Update the Status property of a Notion page. Use to flag items for review after audit discrepancies.",
        inputSchema: {
            page_id: z.string().describe("Notion page ID to update"),
            status: z.string().describe("New status value (e.g. 'Flagged for Review')"),
        }
    },
    async (args: any) => {
        try {
            const result = await executeUpdateBookStatus(args);
            return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error occurred";
            return {
                content: [{ type: "text", text: `Error: ${message}. Ensure the page has a Status property and the integration has update access.` }],
                isError: true,
            };
        }
    }
);

server.registerTool(
    "request_human_signature",
    {
        description: "Record a finding that requires human authorization. Returns PENDING_HUMAN_REVIEW — does NOT indicate approval; human must explicitly approve before update_book_status. Reference stub; actual interactive gate is in Python orchestrator.",
        inputSchema: {
            finding_summary: z.string().min(1).describe("Summary of the finding requiring human sign-off"),
            severity: z.string().min(1).describe("Severity of the finding (e.g. HIGH)"),
        }
    },
    async (args: any) => {
        try {
            const result = executeRequestHumanSignature(args);
            return { content: [{ type: "text", text: result }] };
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error occurred";
            return {
                content: [{ type: "text", text: `Error: ${message}. Ensure finding_summary and severity are provided.` }],
                isError: true,
            };
        }
    }
);

server.registerTool(
    "analyze_artifact_vision",
    {
        description: "Sovereign Vault: Analyze artifact image locally. Resizes to 512x512, sends to local Ollama vision model. Returns structured text only; no image data retained. NEVER route to cloud.",
        inputSchema: {
            image_path: z.string().min(1).describe("Path to artifact image. Resolved relative to SOVEREIGN_VAULT_IMAGE_BASE (default: cwd); path traversal rejected."),
            analysis_focus: z.string().min(1).describe("Focus of analysis (e.g. typography, binding_texture)"),
        }
    },
    async (args: any) => {
        try {
            const result = await executeAnalyzeArtifactVision(args);
            return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error occurred";
            return {
                content: [{ type: "text", text: `Error: ${message}. Ensure image_path exists and Ollama is running with a vision model.` }],
                isError: true,
            };
        }
    }
);

server.registerTool(
    "create_audit_log",
    {
        description: "Create a permanent audit log entry in the Audit Logs database. Call after every audit to maintain a record.",
        inputSchema: {
            book_title: z.string().describe("Title of the book audited"),
            catalog_page_id: z.string().describe("Notion page ID of the book from search_books or find_book_in_master_bibliography; links audit to the catalog entry"),
            result: z.enum(["Pass", "Flagged", "Fail"]).describe("Audit result"),
            summary: z.string().describe("Brief summary of the audit findings"),
            full_report: z.string().describe("Full audit report (JSON or detailed text)"),
            audit_date: z.string().optional().default(() => new Date().toISOString()).describe("ISO 8601 date string; defaults to current time if not provided"),
        }
    },
    async (args: any) => {
        try {
            const result = await executeCreateAuditLog(args);
            return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error occurred";
            return {
                content: [{ type: "text", text: `Error: ${message}. Ensure NOTION_AUDIT_LOG_DATABASE_ID is set and the database has title (primary), Linked Book (relation), Audit Date, Result, Summary, and Full Report properties.` }],
                isError: true,
            };
        }
    }
);

// --- TOOL REGISTRATION END ---

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Rare Books Intelligence MCP Server running on stdio");
}

main().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
});