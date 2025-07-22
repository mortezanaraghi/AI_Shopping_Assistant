# ADR-003: Tiered Code Generation Tools (`codegen_fast` vs. `codegen_slow`)

**Date:** 2025-07-20

**Status:** Accepted

## Context

The Product.ai system requires the ability to answer user questions that involve real-time calculations, data transformations, or complex comparisons that cannot be pre-programmed. Examples include:

*   "What is $1500 minus a 20% discount?" (Simple arithmetic)
*   "Which of these three laptops has the best screen brightness-to-price ratio?" (Complex calculation and data extraction)
*   "Rank these cameras by a weighted score of 60% sensor size and 40% battery life." (Custom data transformation and ranking)

A single, powerful Large Language Model (LLM) could theoretically generate Python code to answer all of these. However, the most powerful models (e.g., GPT-4-Turbo) have higher latency and significantly higher cost per token compared to smaller, faster models (e.g., GPT-4o-mini). Using a top-tier model for every simple calculation would be inefficient, costly, and would negatively impact the user experience by adding unnecessary latency to simple queries.

We needed a strategy that could provide the robust reasoning of a powerful model for complex tasks while offering the speed and cost-efficiency of a smaller model for simple tasks.

## Decision

We will implement a **tiered, "latency ladder" approach** to on-demand code generation by introducing two distinct tools available to the orchestrator:

1.  **`codegen_fast`**:
    *   **Underlying Model:** A smaller, faster, and cheaper LLM (e.g., GPT-4o-mini, Llama3-8B).
    *   **Purpose:** Optimized for simple, low-ambiguity tasks like basic arithmetic, percentage calculations, or simple data extractions.
    *   **Behavior:** It is expected to be the default choice for any calculation.

2.  **`codegen_slow`**:
    *   **Underlying Model:** A larger, more powerful, but more expensive LLM (e.g., GPT-4-Turbo, Claude 3 Opus).
    *   **Purpose:** Reserved for complex, multi-step calculations, custom ranking logic, or data analysis that requires deeper reasoning and a better understanding of intent.
    *   **Behavior:** It serves as an escalation path.

The `DynamicOrchestrator` will be explicitly prompted to **always attempt to use `codegen_fast` first**. Only if `codegen_fast` fails to produce correct or executable code for the task at hand should the orchestrator's reasoning loop decide to escalate and retry the same task with `codegen_slow`.

## Consequences

### Positive

*   **Improved User Experience:** Simple, common calculations will be resolved with very low latency, making the assistant feel more responsive and snappy.
*   **Significant Cost Reduction:** The vast majority of code generation tasks are simple. By defaulting to a cheaper model, we drastically reduce our operational costs per session.
*   **Optimized Resource Allocation:** We use our most powerful (and expensive) AI resources only when absolutely necessary, ensuring they are reserved for the tasks that provide the most value.
*   **Enhanced Robustness:** The tiered system still retains the ability to solve complex problems using the powerful `codegen_slow` model, so we don't sacrifice capability. The fallback mechanism provides a built-in robustness layer.

### Negative

*   **Increased Orchestration Complexity:** The orchestrator's reasoning prompt must now include logic for tool selection and escalation, making it slightly more complex.
*   **Potential for Increased Latency on Complex Tasks:** For a task that truly requires `codegen_slow`, the system will first attempt and fail with `codegen_fast`, adding one extra LLM round-trip to the total processing time. However, we assess this as an acceptable trade-off, as these complex queries are far less common.
*   **Maintenance Overhead:** We now have two distinct tools to maintain, monitor, and potentially update. 