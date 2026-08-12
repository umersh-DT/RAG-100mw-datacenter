# Import sys and Path to handle project imports cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import standard library modules
import json
import yaml
from scripts.generation.qa_generator import GroundedQAGenerator

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Verify configuration file exists before execution
if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Configuration file missing at {CONFIG_PATH.resolve()}")

# Load pipeline configuration
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

BENCHMARK_FILE = Path(config["evaluation"]["benchmark_file"])
RESULTS_OUTPUT_FILE = Path(config["evaluation"]["results_output_file"])
RESULTS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


def evaluate_retrieval_and_grounding():
    """Evaluates RAG pipeline performance against golden_qna.json benchmark."""
    if not BENCHMARK_FILE.exists():
        raise FileNotFoundError(f"Benchmark file missing at {BENCHMARK_FILE.resolve()}")

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    qa_engine = GroundedQAGenerator()

    total_queries = len(golden_data)
    correct_retrievals = 0
    grounding_scores = []
    results = []

    print(f"\n[INFO] Running evaluation across {total_queries} benchmark queries...\n")

    for test_case in golden_data:
        query_id = test_case["query_id"]
        question = test_case["question"]
        expected_file = test_case["source_file"]
        ground_truth = test_case["ground_truth"]
        meta_filter = test_case.get("metadata_filter", None)

        # Run pipeline
        answer, retrieved_chunks = qa_engine.generate_answer(question, metadata_filter=meta_filter)

        # 1. Evaluate Retrieval Success (Did top chunks contain the expected source file?)
        retrieved_sources = [chunk["metadata"]["source_file"] for chunk in retrieved_chunks]
        hit = expected_file in retrieved_sources
        if hit:
            correct_retrievals += 1

        # 2. Evaluate Grounding Match (Check key terms presence)
        gt_words = set(ground_truth.lower().replace(",", "").replace(".", "").split())
        ctx_text = " ".join([c["text"] for c in retrieved_chunks]).lower()
        matched_words = [word for word in gt_words if len(word) > 3 and word in ctx_text]
        grounding_score = len(matched_words) / max(1, len([w for w in gt_words if len(w) > 3]))
        grounding_scores.append(grounding_score)

        results.append({
            "query_id": query_id,
            "question": question,
            "expected_source": expected_file,
            "retrieved_sources": retrieved_sources,
            "retrieval_hit": hit,
            "grounding_score": round(grounding_score, 4)
        })

    # Summary metrics
    context_recall = correct_retrievals / total_queries
    avg_grounding = sum(grounding_scores) / len(grounding_scores)

    summary = {
        "context_recall": round(context_recall, 4),
        "grounding_accuracy": round(avg_grounding, 4),
        "total_queries_tested": total_queries,
        "successful_retrievals": correct_retrievals
    }

    output_payload = {
        "summary_metrics": summary,
        "detailed_results": results
    }

    with open(RESULTS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("================ EVALUATION SUMMARY ================")
    print(f"Context Recall (Source Accuracy): {context_recall * 100:.1f}%")
    print(f"Grounding Accuracy:             {avg_grounding * 100:.1f}%")
    print(f"Detailed results saved to:      {RESULTS_OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    evaluate_retrieval_and_grounding()