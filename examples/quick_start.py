"""
Quick Start — The 5-Minute Forensic Audit.

A streamlined entry point that demonstrates the full Sovereign Vault 
architecture: Local Vision -> Redaction -> Cloud Reasoning.
"""

import sys
import argparse
from orchestrator import run_forensic_audit

def main():
    parser = argparse.ArgumentParser(description="MCP Forensic Quick Start")
    parser.add_argument(
        "--artifact", 
        default="./test_images/sample_gatsby.jpg",
        help="Path to the artifact image for analysis"
    )
    args = parser.parse_args()

    print("\n🚀 Starting Sovereign Vault Quick Start...")
    print("------------------------------------------")
    print(f"👁️  Perception: Local Llama 3.2 Vision")
    print(f"🛡️  Security: Sovereign Redactor Active")
    print(f"🧠 Reasoning: Anthropic Claude 3.5")
    print("------------------------------------------\n")

    # Run a standardized audit on a known sample
    try:
        run_forensic_audit(
            image_path=args.artifact,
            title="The Great Gatsby",
            analysis_focus="Verification of first-edition points of issue and marginalia.",
            provider="anthropic" # Defaulting to cloud to show redaction
        )
        print("\n✅ Audit Complete. Final report saved to build_forensic_report.md")
    except Exception as e:
        print(f"\n❌ Audit Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()