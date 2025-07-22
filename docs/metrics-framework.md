# Evaluation & Metrics Framework

**Objective**: This document defines a comprehensive framework for the continuous evaluation, measurement, and improvement of the Product.ai Shopping Assistant. Our goal is to move beyond basic system health metrics to a sophisticated understanding of conversation quality and expert-level guidance.

---

## 1. Core Principles

1.  **User Success is Paramount**: Our primary metric for success is whether the user accomplished their shopping goal.
2.  **Quality over Quantity**: A single, high-quality, expert-level response is more valuable than multiple low-quality turns.
3.  **Data-Driven Improvement**: All improvements to agents, prompts, or workflows must be validated by measurable changes in our core metrics.
4.  **Automate Where Possible**: We will leverage automation, including LLM-as-a-judge, to provide consistent and scalable quality assessment.

---

## 2. Automated Evaluation System

To ensure consistent and scalable quality control, we will implement an automated evaluation pipeline. This system will run nightly against a curated "test battery" of challenging queries and edge cases.

### 2.1. The Test Battery

*   A collection of test cases stored in a structured format (e.g., YAML or JSON).
*   Each test case includes:
    *   `query`: The input user query.
    *   `context`: Any necessary conversation history or user profile data.
    *   `expected_outcome`: A description of the ideal response (e.g., "Should identify the product is out of stock," "Should recommend at least 3 laptops under $1500").
    *   `expected_tools`: A list of tools that should ideally be used.

### 2.2. LLM-as-a-Judge

The core of the system is an evaluation service that uses a powerful LLM (e.g., GPT-4o) as a judge.

**Workflow**:
1.  For each test case in the battery, the system sends the query to the Product.ai assistant.
2.  The assistant's final response is captured.
3.  A carefully crafted prompt is sent to the judge LLM, containing:
    *   The original query and context.
    *   The assistant's response.
    *   The `expected_outcome`.
    *   A rubric of metrics to evaluate against.
4.  The judge LLM returns a structured JSON object with scores and rationale for each metric.

### 2.3. Key Evaluation Metrics

The following metrics will be calculated by the LLM-as-a-judge for each test case.

| Metric        | Definition                                                                                                   | Calculation Method                                                                                                            |
| :------------ | :----------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| **Correctness** | Does the response contain factually accurate information?                                                      | **Binary (0 or 1)**. The judge verifies facts in the response against the provided `expected_outcome`.                        |
| **Completeness**| Does the response address all parts of the user's query?                                                       | **Scale (0.0 to 1.0)**. The judge calculates the ratio of sub-queries answered to the total number of sub-queries.            |
| **Conciseness** | Is the response free of irrelevant or redundant information?                                                   | **Scale (0.0 to 1.0)**. The judge assesses the proportion of the response that is directly relevant to the query.             |
| **Relevance**   | Is the answer directly related to the user's stated and implied intent?                                      | **Scale (0.0 to 1.0)**. A semantic similarity score between the query and the response, as determined by the judge.         |
| **Helpfulness** | How well does the response help the user achieve their goal? (A weighted combination of the above metrics).  | **Scale (1 to 5)**. The judge's overall score, considering if the answer is actionable and insightful.                      |
| **Tool Accuracy** | Did the system use the appropriate tools to answer the query?                                                | **Jaccard Index**. The similarity between the set of `expected_tools` and the set of tools actually used by the assistant.    |

---

## 3. Key Performance Indicators (KPIs) & Monitoring

These metrics will be tracked in our monitoring dashboards (e.g., Grafana) to provide a real-time view of system health and quality.

### 3.1. User-Facing KPIs

*   **Conversation Quality Score (CQS)**: The average `Helpfulness` score from the nightly automated evaluation run. Our north-star metric.
*   **Task Success Rate (TSR)**: The percentage of conversations where the user's goal is met. Initially measured via the automated evaluation (`Correctness` > 0 and `Completeness` > 0.8), with plans to incorporate user feedback.
*   **User Engagement**:
    *   *Turns Per Session*: The average number of messages exchanged.
    *   *Session Duration*: The average length of a user session.

### 3.2. System-Facing KPIs

*   **Agent Performance**:
    *   *Latency*: p50, p90, and p99 response times for each agent.
    *   *Error Rate*: Percentage of agent executions that result in an error.
    *   *Confidence Score Distribution*: Average confidence score per agent, to track calibration.
*   **Tool Usage & Performance**:
    *   *Tool Call Frequency*: A count of how often each tool is used, to identify the most critical dependencies.
    *   *Tool Error Rate*: The failure rate of external API calls.
*   **Cache Performance**:
    *   *Cache Hit Rate*: The percentage of requests served from the Redis cache, broken down by data type (e.g., user profiles, price data).

---

## 4. Continuous Improvement Loop

The metrics and evaluation system feed a structured process for continuous improvement.

1.  **Daily Review**: The CQS and other automated evaluation metrics are reviewed daily. Any significant regression triggers an immediate investigation.
2.  **Weekly Performance Meeting**: A cross-functional team (Product, Engineering) reviews the KPI dashboards to identify trends, underperforming agents, or common user problems.
3.  **Hypothesize & A/B Test**: Based on the review, the team can propose improvements (e.g., "Refining the prompt for the `ProductDiscoveryAgent` will improve its relevance score"). These changes are deployed as A/B tests.
4.  **Measure & Iterate**: The impact of the change is measured against our core KPIs. Successful experiments are rolled out to all users. This data-driven loop ensures that we are constantly and measurably improving the quality of our assistant.

 