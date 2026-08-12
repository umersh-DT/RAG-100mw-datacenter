# Import os module for system path operations
import os
# Import json module to serialize and write structured benchmark files
import json
# Import yaml module to read central pipeline settings
import yaml
# Import Path from pathlib for safe cross-platform file paths
from pathlib import Path

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Verify configuration file exists before executing logic
if not CONFIG_PATH.exists():
    # Raise descriptive error if config file is missing
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Open central configuration YAML file in read mode
with open(CONFIG_PATH, "r") as f:
    # Parse YAML contents into a Python dictionary
    config = yaml.safe_load(f)

# Resolve target path for evaluation directory from config
EVAL_DIR = Path(config["paths"]["evaluation_dir"])
# Ensure target output directory exists on disk
EVAL_DIR.mkdir(parents=True, exist_ok=True)


# Define function to construct and save the golden Q&A dataset
def generate_golden_evaluation_dataset():
    """Generates golden_qna.json benchmark dataset with ground truth answers and citation metadata."""
    # Define full output file path for the JSON benchmark file
    json_filename = EVAL_DIR / "golden_qna.json"
    
    # Construct list of benchmark evaluation objects mapped to generated documents
    golden_dataset = [
        {
            "query_id": "QNA_001",
            "category": "Commercial Legal",
            "question": "What is the base electricity tariff and curtailment limit under the GridCo Power Purchase Agreement?",
            "ground_truth": "The base electricity tariff is locked at $0.058 per kWh for the first five operating years. GridCo reserves the right to execute forced curtailment up to a maximum limit of 40 cumulative hours per calendar year if grid frequency drops below 49.8 Hz.",
            "source_file": "PPA_GridCo_100MW_2025.pdf",
            "expected_page": 1,
            "metadata_filter": {
                "document_type": "Power Purchase Agreement",
                "tax_year": 2025,
                "department": "Legal & Compliance"
            }
        },
        {
            "query_id": "QNA_002",
            "category": "Financial Operations",
            "question": "What was the total billing amount due for Q1 2025 electricity consumption, including energy tax?",
            "ground_truth": "The total amount due for Q1 2025 is $3,361,575.00, which includes $3,201,500.00 in subtotal power supply charges and $160,075.00 in government energy tax (5%).",
            "source_file": "INV_2025_Q1_GridCo_100MW.pdf",
            "expected_page": 1,
            "metadata_filter": {
                "document_type": "TOU Power Invoice",
                "tax_year": 2025,
                "department": "Financial Operations"
            }
        },
        {
            "query_id": "QNA_003",
            "category": "Electrical Engineering",
            "question": "What are the capacity ratings and protection relays assigned to primary step-down transformer XFRM-01?",
            "ground_truth": "XFRM-01 is rated at 50 MVA (132kV/33kV) with a fault current rating of 40 kA (1 sec) and is protected by a SEL-787 Differential relay.",
            "source_file": "SLD_132kV_Substation_01.pdf",
            "expected_page": 1,
            "metadata_filter": {
                "document_type": "Single Line Diagram",
                "department": "Electrical Infrastructure"
            }
        },
        {
            "query_id": "QNA_004",
            "category": "Electrical Engineering",
            "question": "Which circuit breaker tag controls Transformer 1 on the 132kV main utility busbar?",
            "ground_truth": "Circuit breaker tag CB-132-A1 (SF6 Gas Circuit Breaker, 2000A Continuous) controls Transformer 1 (XFRM-01).",
            "source_file": "SLD_132kV_Substation_01.pdf",
            "expected_page": 1,
            "metadata_filter": {
                "document_type": "Single Line Diagram",
                "department": "Electrical Infrastructure"
            }
        }
    ]
    
    # Open target JSON file in write mode with UTF-8 encoding
    with open(json_filename, "w", encoding="utf-8") as f:
        # Dump list of benchmark dictionaries into formatted JSON with indentation
        json.dump(golden_dataset, f, indent=2)
        
    # Print execution success log to console
    print(f"[SUCCESS] Golden Evaluation Dataset generated at: {json_filename.resolve()}")


# Check if script is run directly from command line
if __name__ == "__main__":
    # Execute benchmark dataset generation function
    generate_golden_evaluation_dataset()