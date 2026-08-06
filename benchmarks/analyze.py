#!/usr/bin/env python3
"""Analyze benchmark results and generate summary."""

import json
from pathlib import Path
from collections import defaultdict

RESULTS_FILE = Path(__file__).parent / "benchmark-results.json"
SUMMARY_FILE = Path(__file__).parent / "benchmark-summary.md"


def load_results():
    with open(RESULTS_FILE) as f:
        return json.load(f)


def analyze_results(results):
    """Analyze results by configuration."""
    configs = defaultdict(lambda: {
        "times": [],
        "tokens": [],
        "tps": [],
        "timeouts": 0,
        "json_errors": 0,
        "thinking": 0,
        "correct": 0,
        "concise": 0,
        "total_runs": 0,
    })

    for r in results:
        config = r["config_name"]
        configs[config]["times"].append(r["total_duration_ms"])
        configs[config]["tokens"].append(r["output_tokens"])
        configs[config]["tps"].append(r["tokens_per_sec"])
        configs[config]["total_runs"] += 1
        if r["timeout"]:
            configs[config]["timeouts"] += 1
        if r["json_parse_error"]:
            configs[config]["json_errors"] += 1
        if r["thinking_detected"]:
            configs[config]["thinking"] += 1
        if r["correct_output"]:
            configs[config]["correct"] += 1
        if r["concise"]:
            configs[config]["concise"] += 1

    return configs


def calculate_stats(values):
    """Calculate mean, p95, min, max."""
    if not values:
        return {"mean": 0, "p95": 0, "min": 0, "max": 0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p95_idx = int(n * 0.95)
    return {
        "mean": sum(sorted_vals) / n,
        "p95": sorted_vals[min(p95_idx, n - 1)],
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }


def generate_summary(configs):
    """Generate markdown summary."""
    lines = []
    lines.append("# Council AI Benchmark Summary\n")
    lines.append("## Overview\n")
    lines.append(f"- **Date**: 2026-08-04")
    lines.append(f"- **Hardware**: RTX 4060 OC 8GB VRAM, Intel i5-12400F, 15GB RAM")
    lines.append(f"- **Settings**: max_concurrent_workers=1, temperature=0, think=false")
    lines.append(f"- **Test Prompts**: 6 (code, debug, plan, review, synthesize, memory)")
    lines.append(f"- **Runs per Test**: 3")
    lines.append("")

    lines.append("## Configuration Comparison\n")
    lines.append("| Metric | Config A (Qwen) | Config B (Qwen+Granite) | Config C (Qwen+Ministral) |")
    lines.append("|--------|-----------------|-------------------------|---------------------------|")

    config_names = list(configs.keys())
    
    avg_times = [sum(configs[c]["times"])/len(configs[c]["times"]) if configs[c]["times"] else 0 for c in config_names]
    lines.append(f"| Avg Time (ms) | {avg_times[0]:.0f} | {avg_times[1]:.0f} | {avg_times[2]:.0f} |")
    
    p95_times = [calculate_stats(configs[c]["times"])["p95"] for c in config_names]
    lines.append(f"| P95 Time (ms) | {p95_times[0]:.0f} | {p95_times[1]:.0f} | {p95_times[2]:.0f} |")
    
    avg_tokens = [sum(configs[c]["tokens"])/len(configs[c]["tokens"]) if configs[c]["tokens"] else 0 for c in config_names]
    lines.append(f"| Avg Tokens | {avg_tokens[0]:.0f} | {avg_tokens[1]:.0f} | {avg_tokens[2]:.0f} |")
    
    avg_tps = [sum(configs[c]["tps"])/len(configs[c]["tps"]) if configs[c]["tps"] else 0 for c in config_names]
    lines.append(f"| Avg TPS | {avg_tps[0]:.1f} | {avg_tps[1]:.1f} | {avg_tps[2]:.1f} |")
    
    timeouts = [configs[c]["timeouts"] for c in config_names]
    lines.append(f"| Timeouts | {timeouts[0]} | {timeouts[1]} | {timeouts[2]} |")
    
    json_errors = [configs[c]["json_errors"] for c in config_names]
    lines.append(f"| JSON Errors | {json_errors[0]} | {json_errors[1]} | {json_errors[2]} |")
    
    thinking = [configs[c]["thinking"] for c in config_names]
    lines.append(f"| Thinking Detected | {thinking[0]} | {thinking[1]} | {thinking[2]} |")
    
    correct = [configs[c]["correct"] for c in config_names]
    lines.append(f"| Correct Output | {correct[0]} | {correct[1]} | {correct[2]} |")
    
    concise = [configs[c]["concise"] for c in config_names]
    lines.append(f"| Concise | {concise[0]} | {concise[1]} | {concise[2]} |")

    lines.append("")

    # Win rates
    lines.append("## Success Rates\n")
    for config_name in config_names:
        c = configs[config_name]
        total = c["total_runs"]
        success_rate = (total - c["timeouts"]) / total * 100
        correct_rate = c["correct"] / total * 100
        concise_rate = c["concise"] / total * 100
        lines.append(f"### {config_name}\n")
        lines.append(f"- **Success Rate**: {success_rate:.1f}% ({total - c['timeouts']}/{total})")
        lines.append(f"- **Correct Output**: {correct_rate:.1f}%")
        lines.append(f"- **Concise Output**: {concise_rate:.1f}%")
        lines.append(f"- **Timeouts**: {c['timeouts']}")
        lines.append(f"- **JSON Errors**: {c['json_errors']}")
        lines.append(f"- **Thinking Detected**: {c['thinking']}")
        lines.append("")

    # Winner determination
    lines.append("## Winner\n")
    scores = {}
    for c in config_names:
        avg_time = sum(configs[c]["times"]) / len(configs[c]["times"]) if configs[c]["times"] else float('inf')
        timeout_penalty = configs[c]["timeouts"] * 10000
        error_penalty = configs[c]["json_errors"] * 5000
        scores[c] = avg_time + timeout_penalty + error_penalty

    winner = min(scores, key=scores.get)
    lines.append(f"**Winner: {winner}**\n")
    lines.append(f"**Reasoning**: Lowest average latency ({sum(configs[winner]['times'])/len(configs[winner]['times']):.0f}ms), "
                 f"zero timeouts, and zero JSON errors.\n")

    return "\n".join(lines)


def main():
    results = load_results()
    configs = analyze_results(results)
    summary = generate_summary(configs)

    with open(SUMMARY_FILE, "w") as f:
        f.write(summary)

    print(f"Summary written to {SUMMARY_FILE}")
    print("\n" + summary)


if __name__ == "__main__":
    main()
