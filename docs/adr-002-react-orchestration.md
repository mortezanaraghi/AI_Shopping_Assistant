# ADR-002: Dynamic ReAct-based Orchestration

**Date:** 2025-07-20

**Status:** Accepted

## Context

The core of the Product.ai assistant is its ability to handle complex, multi-step user queries that require the coordination of multiple specialized tools and agents. We considered several architectural patterns for this orchestration logic, primarily:

1.  **Static Workflows / Chains:** Define a fixed, directed acyclic graph (DAG) of operations. A query is classified, and then it follows a predetermined path through the graph. Frameworks like LangChain's basic `chains` or CrewAI's `SequentialProcess` follow this pattern. This approach is predictable and easy to debug.
2.  **LLM as a Pure Function:** Treat the LLM as a single, powerful function. Give it the user query and descriptions of all available tools, and ask it to generate a final answer in one shot, potentially using a function-calling mechanism.
3.  **Dynamic, Iterative Reasoning:** An approach where the orchestrator reasons about the problem step-by-step, executing one tool at a time and then re-evaluating its plan based on the new information. The ReAct (Reason and Act) framework is a prominent example of this pattern.

The primary challenge with static workflows is their rigidity. They fail when a query doesn't fit a predefined path or when a tool returns an unexpected error. The "LLM as a Pure Function" approach often fails on complex tasks that require intermediate steps or error recovery; it has to get everything right in a single pass. We needed a system that was both robust and flexible enough to handle the unpredictable nature of user conversations.

## Decision

We will implement the **Real-Time Engine's orchestrator using a dynamic, iterative ReAct (Reason-Act) model.**

The control flow will be a loop, managed by the `DynamicOrchestrator`, that performs the following steps on each iteration:

1.  **Reason (The "Thinking Step"):** The orchestrator synthesizes the original user query, the full conversation history, the user's profile, and the history of all previous tool executions in the current turn. It feeds this complete context to an LLM and prompts it to form a "thought" about the current state and decide on the *single next action* to take.
2.  **Act:** The orchestrator parses the LLM's desired action. This action can be one of three things:
    *   **Use a Tool:** Invoke a specific tool from the `AgentRegistry` with the provided arguments.
    *   **Ask a Clarifying Question:** Respond to the user to gather more information.
    *   **Provide a Final Answer:** Conclude the loop and deliver the final response to the user.

This loop continues until a final answer is provided or a maximum number of iterations is reached. This model moves the planning logic from a static, predefined structure into a dynamic, runtime process.

## Consequences

### Positive

*   **Enhanced Flexibility and Adaptability:** The system is not confined to predefined paths. It can dynamically chain tools together in novel combinations to solve unforeseen problems.
*   **Superior Error Handling:** The "thinking step" after each action is a powerful error recovery mechanism. If a tool fails or returns unexpected data, the orchestrator can "reason" about the failure and decide on a new course of action, such as trying a different tool or asking the user for help. This makes the system far more resilient than static workflows.
*   **Improved Reasoning on Complex Tasks:** By breaking a complex problem down into smaller, sequential steps, the system is more likely to succeed. The context from each step informs the next, mimicking a human's logical problem-solving process.
*   **Stateful Coherence:** The inclusion of conversation history in every reasoning step ensures that the agent's actions are always coherent with the ongoing dialogue and user intent.

### Negative

*   **Increased Latency:** The iterative nature of the ReAct loop means that a multi-step query will require multiple round-trips to the LLM. This introduces more latency compared to a single-pass approach. However, we deem this an acceptable trade-off for the significant gains in robustness and capability.
*   **Higher Cost for Multi-Step Queries:** More LLM calls directly translate to higher operational costs for complex queries. This is mitigated by our "Latency Ladder" approach for tools like `codegen` and aggressive caching.
*   **Debugging Complexity:** Tracing the "thought process" of the orchestrator can be more complex than following a static graph. This requires robust structured logging of each thought and action to maintain observability.
*   **Risk of "Stuck" Loops:** It's possible for the orchestrator to get stuck in a repetitive loop. This is mitigated by a maximum iteration limit, which acts as a safety valve. 