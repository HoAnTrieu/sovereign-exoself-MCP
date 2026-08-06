# Council AI Benchmark Summary

## Overview

- **Date**: 2026-08-04
- **Hardware**: RTX 4060 OC 8GB VRAM, Intel i5-12400F, 15GB RAM
- **Settings**: max_concurrent_workers=1, temperature=0, think=false
- **Test Prompts**: 6 (code, debug, plan, review, synthesize, memory)
- **Runs per Test**: 3

## Configuration Comparison

| Metric | Config A (Qwen) | Config B (Qwen+Granite) | Config C (Qwen+Ministral) |
|--------|-----------------|-------------------------|---------------------------|
| Avg Time (ms) | 1685 | 1504 | 3188 |
| P95 Time (ms) | 4882 | 3428 | 10353 |
| Avg Tokens | 56 | 87 | 97 |
| Avg TPS | 41.4 | 64.6 | 72.6 |
| Timeouts | 0 | 0 | 0 |
| JSON Errors | 0 | 0 | 0 |
| Thinking Detected | 0 | 0 | 0 |
| Correct Output | 90 | 90 | 90 |
| Concise | 89 | 90 | 90 |

## Success Rates

### Config A - Single Model

- **Success Rate**: 100.0% (90/90)
- **Correct Output**: 100.0%
- **Concise Output**: 98.9%
- **Timeouts**: 0
- **JSON Errors**: 0
- **Thinking Detected**: 0

### Config B - Qwen + Granite

- **Success Rate**: 100.0% (90/90)
- **Correct Output**: 100.0%
- **Concise Output**: 100.0%
- **Timeouts**: 0
- **JSON Errors**: 0
- **Thinking Detected**: 0

### Config C - Qwen + Ministral

- **Success Rate**: 100.0% (90/90)
- **Correct Output**: 100.0%
- **Concise Output**: 100.0%
- **Timeouts**: 0
- **JSON Errors**: 0
- **Thinking Detected**: 0

## Winner

**Winner: Config B - Qwen + Granite**

**Reasoning**: Lowest average latency (1504ms), zero timeouts, and zero JSON errors.
