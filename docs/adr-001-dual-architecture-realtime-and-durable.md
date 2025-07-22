# ADR-001: Dual-Architecture with Real-Time and Durable Engines

**Date:** 2025-07-20

**Status:** Accepted

## Context

The Product.ai assistant must handle a wide spectrum of user interactions that have fundamentally different operational requirements. These interactions can be broadly classified into two categories:

1.  **Synchronous, Conversational Queries:** These are the majority of user interactions. They are short-lived, request-response cycles where low latency is critical for a good user experience. Examples include "What are the specs for this laptop?" or "Compare these two products." A system optimized for this must be highly concurrent and fast.
2.  **Asynchronous, Long-Running Tasks:** These are high-value user requests that must be reliably executed over long periods (minutes, days, or weeks), surviving server restarts, deployments, and other failures. Examples include "Notify me when the price of this camera drops by 15%" or "Watch for this item to come back in stock and buy it for me." A system optimized for this must prioritize durability, fault tolerance, and state persistence over raw speed.

A single architectural pattern cannot efficiently serve both needs. A purely real-time, stateless architecture cannot provide the guarantees required for long-running tasks. Conversely, forcing all simple, conversational queries through a durable workflow engine would introduce unnecessary latency and operational overhead, degrading the user experience and increasing costs.

## Decision

We will implement a **dual-architecture, two-tier system** to handle these distinct use cases. An `Orchestrator Router` will act as the initial entry point for all user requests, intelligently routing them to the appropriate engine based on an analysis of the user's intent.

*   **Tier 1: Real-Time Multi-Agent Engine:**
    *   **Responsibility:** Handles all synchronous, conversational queries.
    *   **Implementation:** A lightweight, stateless application built on Python's `asyncio` to ensure high concurrency and low latency. It will use the dynamic ReAct pattern for orchestration.

*   **Tier 2: Durable Workflow Engine:**
    *   **Responsibility:** Manages all asynchronous, long-running, and stateful tasks.
    *   **Implementation:** Built on **Temporal.io**. This provides the required guarantees of durability, fault tolerance, and state persistence for high-value user journeys.

This approach allows us to use the right tool for the right job, optimizing both the core conversational experience and our ability to offer unique, long-running services.

## Consequences

### Positive

*   **Optimized User Experience:** Simple, common queries are handled by the low-latency real-time engine, ensuring the assistant feels fast and responsive.
*   **Creation of a Powerful Technical Moat:** The Durable Workflow Engine unlocks a new class of high-value, stateful services (e.g., price monitoring, automated purchasing) that are impossible for purely stateless competitors to replicate. This is a major competitive differentiator.
*   **Improved System Resilience:** The two tiers are decoupled. A failure or performance degradation in the real-time engine (e.g., due to a traffic spike) will not affect the execution of durable, business-critical workflows managed by Temporal.
*   **Efficient Resource Utilization:** We avoid the significant overhead of the durable execution framework for the 80-90% of queries that are simple and conversational, leading to lower operational costs.
*   **Clear Separation of Concerns:** Developers have a clear distinction between the two programming models, making it easier to reason about the system and place new functionality in the appropriate tier.

### Negative

*   **Increased Architectural Complexity:** We now have two distinct execution environments to develop, deploy, monitor, and maintain, each with its own patterns and best practices.
*   **The Router is a Critical Component:** The logic within the `Orchestrator Router` that classifies and routes requests is now a critical single point of failure. An incorrect classification could lead to a task failing or performing poorly. This component will require robust testing and monitoring.
*   **Developer Cognitive Load:** Team members must be proficient in both stateless `asyncio` programming and the stateful, deterministic constraints of Temporal workflows.
*   **Potential for Context Fragmentation:** Ensuring that user context (e.g., profile information) is consistently available and shared between the two tiers requires careful design of the shared state layer (Redis). 