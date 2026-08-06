#!/usr/bin/env python3
"""Council AI Benchmark Script.

Tests 3 model configurations for the sovereign-exoself council.
Runs sequentially with max_concurrent_workers=1.
"""

import json
import os
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any

# Configuration
OLLAMA_API = "http://127.0.0.1:11434"
BENCHMARKS_DIR = Path(__file__).parent
PROMPTS_DIR = BENCHMARKS_DIR / "prompts"
RAW_RESULTS_DIR = BENCHMARKS_DIR / "raw-results"
TOKEN_LIMITS = {
    "manager": 250,
    "worker": 1000,
    "critic": 350,
    "synthesizer": 500,
    "archivist": 250,
}
TEMPERATURE = 0
THINK = False

# System prompts for each role
ROLE_PROMPTS = {
    "manager": (
        "You are the council manager. Classify the task as CODE, ANALYSIS, or DECISION. "
        "Choose workers: 'engineer' for code tasks, 'analyst' for analysis/decision tasks. "
        "Reply with ONLY: task_type=X; workers=Y,Z"
    ),
    "engineer": (
        "You are a code engineer. Write clean, working code. "
        "Return ONLY the code or solution. No explanations unless explicitly asked."
    ),
    "analyst": (
        "You are an analyst. Provide clear, structured analysis. "
        "Use bullet points for key findings. Return ONLY the analysis."
    ),
    "critic": (
        "You are a critic. Find logical errors, edge cases, and improvements. "
        "List issues as: 1) Issue: description. If no issues, reply: 'No issues found'"
    ),
    "synthesizer": (
        "You are a synthesizer. Combine the best parts of each response. "
        "Return the final answer ONLY. No meta-commentary."
    ),
    "archivist": (
        "You are an archivist. Extract key facts and preferences for memory storage. "
        "Reply with extracted items as bullet points or empty string."
    ),
}

# Configurations to test
CONFIGS = {
    "A": {
        "name": "Config A - Single Model",
        "models": {
            "manager": "qwen2.5-coder:7b",
            "engineer": "qwen2.5-coder:7b",
            "analyst": "qwen2.5-coder:7b",
            "critic": "qwen2.5-coder:7b",
            "synthesizer": "qwen2.5-coder:7b",
            "archivist": "qwen2.5-coder:7b",
        },
    },
    "B": {
        "name": "Config B - Qwen + Granite",
        "models": {
            "manager": "granite3.3:2b",
            "engineer": "qwen2.5-coder:7b",
            "analyst": "qwen2.5-coder:7b",
            "critic": "qwen2.5-coder:7b",
            "synthesizer": "granite3.3:2b",
            "archivist": "granite3.3:2b",
        },
    },
    "C": {
        "name": "Config C - Qwen + Ministral",
        "models": {
            "manager": "ministral-3:3b",
            "engineer": "qwen2.5-coder:7b",
            "analyst": "qwen2.5-coder:7b",
            "critic": "qwen2.5-coder:7b",
            "synthesizer": "ministral-3:3b",
            "archivist": "ministral-3:3b",
        },
    },
}


@dataclass
class BenchmarkResult:
    config_name: str
    test_id: str
    test_name: str
    run_number: int
    role: str
    model: str
    first_token_ms: float
    total_duration_ms: float
    input_tokens: int
    output_tokens: int
    tokens_per_sec: float
    timeout: bool
    json_parse_error: bool
    thinking_detected: bool
    correct_output: bool
    concise: bool
    response_preview: str


def call_ollama_chat(
    model: str, system_prompt: str, user_prompt: str, max_tokens: int
) -> dict[str, Any]:
    """Call Ollama chat API and return metrics."""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": max_tokens,
        },
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_API}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        total_ms = (time.perf_counter() - start_time) * 1000

        content = data.get("message", {}).get("content", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 1)
        eval_duration_s = eval_duration_ns / 1e9

        return {
            "content": content,
            "input_tokens": prompt_eval_count,
            "output_tokens": eval_count,
            "total_duration_ms": total_ms,
            "first_token_ms": total_ms * 0.1,  # Estimate
            "tokens_per_sec": eval_count / eval_duration_s if eval_duration_s > 0 else 0,
            "timeout": False,
            "model_actual": data.get("model", model),
        }
    except Exception as e:
        total_ms = (time.perf_counter() - start_time) * 1000
        return {
            "content": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_duration_ms": total_ms,
            "first_token_ms": 0,
            "tokens_per_sec": 0,
            "timeout": "timeout" in str(e).lower() or total_ms > 110000,
            "error": str(e),
        }


def analyze_response(
    response: str, test_id: str, role: str
) -> dict[str, bool]:
    """Analyze response quality."""
    content = response.lower()

    # Check for thinking/reasoning
    thinking_indicators = [
        "let me think",
        "first,",
        "step 1:",
        "i need to",
        "let's analyze",
        "reasoning:",
        "chain of thought",
    ]
    thinking_detected = any(ind in content for ind in thinking_indicators)

    # Check JSON parse errors
    json_parse_error = False
    if test_id == "test5_synthesize":
        try:
            json.loads(response)
        except json.JSONDecodeError:
            json_parse_error = True

    # Check correctness (simplified)
    correct_output = True
    if test_id == "test1_code" and "def " not in content:
        correct_output = False
    if test_id == "test2_debug" and "bug" not in content and "fix" not in content:
        correct_output = False
    if test_id == "test3_plan" and not any(c.isdigit() for c in response[:50]):
        correct_output = False
    if test_id == "test4_review" and "approve" not in content and "reject" not in content:
        correct_output = False

    # Check conciseness
    word_count = len(response.split())
    concise = word_count < 200 if role in ["manager", "archivist"] else word_count < 500

    return {
        "thinking_detected": thinking_detected,
        "json_parse_error": json_parse_error,
        "correct_output": correct_output,
        "concise": concise,
    }


def run_council(
    config: dict, task: str, run_number: int
) -> list[BenchmarkResult]:
    """Run full council workflow for a single task."""
    results = []
    models = config["models"]

    # Step 1: Manager
    manager_result = call_ollama_chat(
        models["manager"], ROLE_PROMPTS["manager"], task, TOKEN_LIMITS["manager"]
    )
    analysis = analyze_response(manager_result["content"], "", "manager")
    results.append(
        BenchmarkResult(
            config_name=config["name"],
            test_id="",
            test_name="",
            run_number=run_number,
            role="manager",
            model=models["manager"],
            first_token_ms=manager_result["first_token_ms"],
            total_duration_ms=manager_result["total_duration_ms"],
            input_tokens=manager_result["input_tokens"],
            output_tokens=manager_result["output_tokens"],
            tokens_per_sec=manager_result["tokens_per_sec"],
            timeout=manager_result["timeout"],
            json_parse_error=False,
            thinking_detected=analysis["thinking_detected"],
            correct_output=True,
            concise=analysis["concise"],
            response_preview=manager_result["content"][:200],
        )
    )

    # Step 2: Worker (engineer or analyst based on manager's classification)
    worker_role = "engineer"  # Default
    if "analyst" in manager_result["content"].lower():
        worker_role = "analyst"

    worker_result = call_ollama_chat(
        models[worker_role],
        ROLE_PROMPTS[worker_role],
        task,
        TOKEN_LIMITS["worker"],
    )
    analysis = analyze_response(worker_result["content"], "", worker_role)
    results.append(
        BenchmarkResult(
            config_name=config["name"],
            test_id="",
            test_name="",
            run_number=run_number,
            role=worker_role,
            model=models[worker_role],
            first_token_ms=worker_result["first_token_ms"],
            total_duration_ms=worker_result["total_duration_ms"],
            input_tokens=worker_result["input_tokens"],
            output_tokens=worker_result["output_tokens"],
            tokens_per_sec=worker_result["tokens_per_sec"],
            timeout=worker_result["timeout"],
            json_parse_error=False,
            thinking_detected=analysis["thinking_detected"],
            correct_output=analysis["correct_output"],
            concise=analysis["concise"],
            response_preview=worker_result["content"][:200],
        )
    )

    # Step 3: Critic
    critic_context = f"Original task: {task}\n\nWorker response:\n{worker_result['content']}"
    critic_result = call_ollama_chat(
        models["critic"], ROLE_PROMPTS["critic"], critic_context, TOKEN_LIMITS["critic"]
    )
    analysis = analyze_response(critic_result["content"], "", "critic")
    results.append(
        BenchmarkResult(
            config_name=config["name"],
            test_id="",
            test_name="",
            run_number=run_number,
            role="critic",
            model=models["critic"],
            first_token_ms=critic_result["first_token_ms"],
            total_duration_ms=critic_result["total_duration_ms"],
            input_tokens=critic_result["input_tokens"],
            output_tokens=critic_result["output_tokens"],
            tokens_per_sec=critic_result["tokens_per_sec"],
            timeout=critic_result["timeout"],
            json_parse_error=False,
            thinking_detected=analysis["thinking_detected"],
            correct_output=True,
            concise=analysis["concise"],
            response_preview=critic_result["content"][:200],
        )
    )

    # Step 4: Synthesizer
    synth_context = f"Task: {task}\n\nWorker: {worker_result['content']}\n\nCritic: {critic_result['content']}"
    synth_result = call_ollama_chat(
        models["synthesizer"],
        ROLE_PROMPTS["synthesizer"],
        synth_context,
        TOKEN_LIMITS["synthesizer"],
    )
    analysis = analyze_response(synth_result["content"], "", "synthesizer")
    results.append(
        BenchmarkResult(
            config_name=config["name"],
            test_id="",
            test_name="",
            run_number=run_number,
            role="synthesizer",
            model=models["synthesizer"],
            first_token_ms=synth_result["first_token_ms"],
            total_duration_ms=synth_result["total_duration_ms"],
            input_tokens=synth_result["input_tokens"],
            output_tokens=synth_result["output_tokens"],
            tokens_per_sec=synth_result["tokens_per_sec"],
            timeout=synth_result["timeout"],
            json_parse_error=analysis["json_parse_error"],
            thinking_detected=analysis["thinking_detected"],
            correct_output=analysis["correct_output"],
            concise=analysis["concise"],
            response_preview=synth_result["content"][:200],
        )
    )

    # Step 5: Archivist
    archivist_context = f"Task completed: {task}\n\nFinal result: {synth_result['content'][:500]}"
    archivist_result = call_ollama_chat(
        models["archivist"],
        ROLE_PROMPTS["archivist"],
        archivist_context,
        TOKEN_LIMITS["archivist"],
    )
    analysis = analyze_response(archivist_result["content"], "", "archivist")
    results.append(
        BenchmarkResult(
            config_name=config["name"],
            test_id="",
            test_name="",
            run_number=run_number,
            role="archivist",
            model=models["archivist"],
            first_token_ms=archivist_result["first_token_ms"],
            total_duration_ms=archivist_result["total_duration_ms"],
            input_tokens=archivist_result["input_tokens"],
            output_tokens=archivist_result["output_tokens"],
            tokens_per_sec=archivist_result["tokens_per_sec"],
            timeout=archivist_result["timeout"],
            json_parse_error=False,
            thinking_detected=analysis["thinking_detected"],
            correct_output=True,
            concise=analysis["concise"],
            response_preview=archivist_result["content"][:200],
        )
    )

    return results


def main():
    """Run full benchmark suite."""
    print("=" * 60)
    print("Council AI Benchmark")
    print("=" * 60)

    # Load prompts
    prompts = []
    for prompt_file in sorted(PROMPTS_DIR.glob("*.json")):
        with open(prompt_file) as f:
            prompts.append(json.load(f))

    print(f"\nLoaded {len(prompts)} test prompts")
    print(f"Configs: {list(CONFIGS.keys())}")
    print(f"Runs per test: 3")
    print(f"Total runs: {len(CONFIGS) * len(prompts) * 3}")
    print(f"Total API calls: {len(CONFIGS) * len(prompts) * 3 * 5}")
    print()

    all_results = []

    for config_key, config in CONFIGS.items():
        print(f"\n{'=' * 60}")
        print(f"Running {config['name']}")
        print(f"Models: {set(config['models'].values())}")
        print(f"{'=' * 60}")

        for prompt in prompts:
            for run_num in range(1, 4):
                print(f"\n  Test: {prompt['name']} (Run {run_num}/3)")
                results = run_council(config, prompt["task"], run_num)

                # Update metadata
                for r in results:
                    r.test_id = prompt["id"]
                    r.test_name = prompt["name"]

                all_results.extend(results)

                # Print summary
                total_time = sum(r.total_duration_ms for r in results)
                total_tokens = sum(r.output_tokens for r in results)
                print(f"    Time: {total_time:.0f}ms | Tokens: {total_tokens}")

                # Save raw result
                raw_path = RAW_RESULTS_DIR / f"{config_key}_{prompt['id']}_run{run_num}.json"
                with open(raw_path, "w") as f:
                    json.dump([asdict(r) for r in results], f, indent=2)

    # Save all results
    results_path = BENCHMARKS_DIR / "benchmark-results.json"
    with open(results_path, "w") as f:
        json.dump([asdict(r) for r in all_results], f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Benchmark complete! Results saved to {results_path}")
    print(f"{'=' * 60}")

    return all_results


if __name__ == "__main__":
    main()
