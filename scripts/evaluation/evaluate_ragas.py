# Import sys and Path to ensure root project imports function cleanly
import sys
# Import Path from pathlib for safe cross-platform file path handling
from pathlib import Path
# Append project root directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import os module for environment and file path operations
import os
# Import json module to read golden datasets and save evaluation results
import json
# Import yaml module to parse pipeline settings
import yaml
# Import Dataset class from Hugging Face datasets library required by Ragas
from datasets import Dataset
# Import Ragas evaluation metrics
from ragas.metrics import faithfulness, answer_relevance, context_recall
# Import Ragas evaluate function to run batch evaluations
from ragas import evaluate
# Import GroundedQAGenerator from our generation pipeline
from scripts.generation.qa_generator import GroundedQAGenerator

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Verify configuration file exists before proceeding
if not CONFIG_PATH.exists():
    # Raise descriptive FileNotFoundError if config path is broken
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Open central configuration YAML file in read mode
with open(CONFIG_PATH, "r") as f:
    # Parse YAML contents into a structured Python dictionary
    config = yaml.safe_load(f)

# Resolve path for benchmark dataset input file
BENCHMARK_FILE = Path(config["evaluation"]["benchmark_file"])
# Resolve path for evaluation results output file
RESULTS_OUTPUT_FILE = Path(config["evaluation"]["results_output_file"])
# Ensure output directory exists on disk
RESULTS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


def run_ragas_evaluation():
    """Runs the Golden Q&A benchmark suite through RAG pipeline and computes Ragas metrics."""
    # Check if benchmark dataset file exists
    if not BENCHMARK_FILE.exists():
        # Raise error if golden_qna.json is missing
        raise FileNotFoundError(f"Benchmark dataset missing at {BENCHMARK_FILE.resolve()}. Run gen_evaluation_dataset.py first.")
        
    # Open and load benchmark dataset
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        # Parse JSON payload into list of evaluation test cases
        golden_data = json.load(f)
        
    # Initialize Grounded QA Generator engine
    qa_engine = GroundedQAGenerator()
    
    # Initialize empty lists to collect dataset columns required by Ragas
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    
    # Print status log starting batch generation
    print(f"\n[INFO] Executing RAG pipeline across {len(golden_data)} benchmark questions...")
    
    # Iterate over every test case in the golden dataset
    for test_case in golden_data:
        # Extract query text
        query = test_case["question"]
        # Extract expected ground truth answer
        ground_truth = test_case["ground_truth"]
        # Extract metadata filter if defined
        meta_filter = test_case.get("metadata_filter", None)
        
        # Execute RAG pipeline to generate answer and retrieve candidate context chunks
        generated_answer, retrieved_chunks = qa_engine.generate_answer(query, metadata_filter=meta_filter)
        
        # Extract raw text content from retrieved chunk objects
        chunk_texts = [chunk["text"] for chunk in retrieved_chunks]
        
        # Append data to respective lists
        questions.append(query)
        answers.append(generated_answer)
        contexts.append(chunk_texts)
        ground_truths.append(ground_truth)
        
    # Construct evaluation dataset dictionary in Ragas format
    eval_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    
    # Convert dictionary into Hugging Face Dataset object
    eval_dataset = Dataset.from_dict(eval_dict)
    
    # Print status log starting metric scoring
    print("\n[INFO] Computing Ragas evaluation metrics (Faithfulness, Answer Relevance, Context Recall)...")
    
    # Execute batch evaluation using selected Ragas metrics
    eval_results = evaluate(
        dataset=eval_dataset,
        metrics=[
            faithfulness,
            answer_relevance,
            context_recall
        ]
    )
    
    # Convert evaluation results object to standard Python dictionary
    results_data = eval_results.to_pandas().to_dict(orient="records")
    
    # Prepare final payload containing individual row scores and mean summary metrics
    output_payload = {
        "summary_metrics": {
            "faithfulness": float(eval_results["faithfulness"]),
            "answer_relevance": float(eval_results["answer_relevance"]),
            "context_recall": float(eval_results["context_recall"])
        },
        "detailed_results": results_data
    }
    
    # Save evaluation output payload to JSON file
    with open(RESULTS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Serialize results to JSON with formatting
        json.dump(output_payload, f, indent=2)
        
    # Print summary results to console
    print("\n================ EVALUATION SUMMARY ================")
    print(f"Faithfulness Score:      {eval_results['faithfulness']:.4f} (Target: {config['evaluation']['target_metrics']['faithfulness']})")
    print(f"Answer Relevance Score:  {eval_results['answer_relevance']:.4f} (Target: {config['evaluation']['target_metrics']['answer_relevance']})")
    print(f"Context Recall Score:     {eval_results['context_recall']:.4f} (Target: {config['evaluation']['target_metrics']['context_recall']})")
    print(f"Detailed results saved to: {RESULTS_OUTPUT_FILE.resolve()}")


# Check if script is executed directly from CLI
if __name__ == "__main__":
    # Execute Ragas evaluation pipeline
    run_ragas_evaluation()