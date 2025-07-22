
# Product.ai: A Dual-Architecture System for Expert-Level Conversational Commerce

**Author:** Morteza Shahbazi

**Date:** July 16, 2024

---

### **Abstract**

The domain of e-commerce has long been constrained by a "conversational gap" between the complex, multi-faceted needs of customers and the simplistic, keyword-driven capabilities of conventional search bars and chatbots. This paper introduces Product.ai, a novel, dual-architecture system designed to bridge this gap by delivering expert-level, human-like guidance at scale. The system synergistically combines a low-latency, real-time multi-agent system for handling high-volume, synchronous queries with a fault-tolerant, durable workflow engine for managing complex, long-running asynchronous tasks. At the core of the system is a dynamic orchestrator that employs a "thinking step" based on the ReAct (Reason and Act) paradigm, allowing it to reason about conversational context and dynamically dispatch tasks to a registry of specialized agents. These agents are equipped with a suite of tools, including on-demand code generation, enabling them to answer previously unanswerable questions that require complex real-time calculations. We detail the system's architecture, the methodology for dynamic agent and workflow orchestration, and robust solutions for scalability and state management. Furthermore, we propose a state-of-the-art evaluation framework based on the "LLM-as-a-Judge" paradigm to ensure continuous improvement and quality control. This paper presents the complete design and rationale for a system that transforms online shopping from a simple transaction into a value-driven, personalized conversation.

---

### **1. Introduction**

The pursuit of artificial conversational intelligence dates back to the earliest days of computing, with Weizenbaum's ELIZA (1966) demonstrating the profound human tendency to attribute intelligence to even simple pattern-matching systems. This early work laid the foundation for the field of Human-Computer Interaction and spawned decades of research into dialogue systems. The historical trajectory of these systems can be broadly categorized into three eras: the era of symbolic, rule-based systems; the era of statistical and machine learning models; and the current era of Large Language Models (LLMs).

Rule-based systems, prevalent until the late 1990s, relied on hand-crafted rules and finite-state machines to manage dialogue flow. While effective in highly constrained domains (e.g., telephone-based flight booking), they were brittle, difficult to scale, and incapable of handling conversational nuance. The rise of statistical methods in the 2000s, particularly Partially Observable Markov Decision Processes (POMDPs), introduced a more flexible, probabilistic approach to dialogue management, but these systems remained data-hungry and computationally expensive.

The modern era, catalyzed by the Transformer architecture (Vaswani et al., 2017) and the subsequent explosion of LLMs like GPT-3 (Brown et al., 2020) and its successors, has fundamentally redefined the landscape. LLMs provide unprecedented fluency, world knowledge, and zero-shot reasoning capabilities. However, deploying them in production environments, especially for complex, task-oriented domains like e-commerce, reveals significant limitations. A single, monolithic LLM often struggles with:

*   **Factual Accuracy and Hallucination:** LLMs can invent plausible but incorrect information, a critical failure in a product-centric domain.
*   **Reasoning Limitations:** While powerful, LLMs can fail at multi-step reasoning or complex calculations without specialized prompting or tools.
*   **State Management:** Standard LLMs are stateless, making it difficult to manage long-term user journeys or asynchronous tasks that span days or weeks.
*   **Cost and Latency:** The computational cost of running large models can be prohibitive for high-volume, real-time applications.

To overcome these challenges, the field is rapidly moving towards multi-agent systems (Sapkota et al., 2025). This paradigm, inspired by distributed artificial intelligence, posits that complex problems are best solved by a collection of smaller, specialized, and coordinated agents rather than a single, monolithic intelligence. These agents can be equipped with specific tools and knowledge, allowing for a more modular, scalable, and robust system design. Recent frameworks like ReAct (Yao et al., 2022) have provided a powerful cognitive blueprint for these agents, enabling them to iteratively **Reason** about a task and determine the best **Act** to take (e.g., use a tool, query a database, or ask the user a clarifying question).

This paper details the architecture and methodology of Product.ai, a system built on these modern principles. It addresses the core problem in conversational commerce: how to translate a vast, structured knowledge base (our proprietary ShopGraph) into expert, trustworthy, and personalized shopping guidance. Our primary contribution is the design of a **dual-architecture system** that leverages the strengths of both real-time multi-agent orchestration and durable, workflow-based processing. This allows Product.ai to handle the full spectrum of customer needs, from immediate product questions to complex, multi-day purchasing journeys, setting a new standard for conversational commerce.

#### **1.1. A Review of Multi-Agent System Architectures**

Before detailing the Product.ai methodology, it is instructive to review the predominant architectural patterns for multi-agent systems in the literature and industry. These patterns primarily differ in their approach to agent coordination and control flow.

1.  **Hierarchical Orchestration:** This is perhaps the most common pattern, exemplified by frameworks like CrewAI and the agentic patterns in LangChain. A top-level "supervisor" or "orchestrator" agent decomposes a complex task into a sequence or graph of sub-tasks. These are then delegated to specialized "worker" agents. The control flow is explicit, predictable, and easier to debug. However, this centralized model can become a bottleneck and is less adaptable to novel problems that don't fit the pre-defined workflow.

2.  **Decentralized / Peer-to-Peer Negotiation:** In this model, agents are autonomous peers that discover, negotiate, and delegate tasks among themselves without a central controller. This architecture promotes emergent behavior and is highly resilient, as there is no single point of failure. Google's A2A (Agent-to-Agent) protocol is a prime example. The primary challenge is maintaining coherence and avoiding chaotic interactions, which requires robust discovery mechanisms and standardized negotiation protocols.

3.  **Event-Driven / Blackboard Systems:** Inspired by early AI systems, this pattern uses a shared, asynchronous data space (the "blackboard") for collaboration. Agents react to events or data posted to the blackboard by other agents. Modern implementations often use event-streaming platforms like Apache Kafka. This architecture is highly scalable and decouples agents effectively but can make it difficult to trace the end-to-end execution of a specific task.

4.  **Brokered Communication:** Here, a central broker or message bus mediates communication between agents. While similar to the orchestrator pattern, the broker is typically less intelligent, focusing on routing, session management, and task queuing rather than task decomposition. This pattern, seen in frameworks like IBM's ACP, is well-suited for enterprise environments requiring auditability and reliable message delivery.

The Product.ai framework synthesizes elements from these patterns into a unique, hybrid model. It uses a **hierarchical orchestrator** for its real-time ReAct cycle but does so in a dynamic, non-predetermined way. The "thinking step" allows the orchestrator to dynamically create a new plan after every action, providing more flexibility than a static DAG. It further combines this with the principles of a **durable, brokered system** via its Temporal.io integration for asynchronous tasks, resulting in an architecture that is both adaptable and resilient.

---

### **2. Methodology: A Dual-Architecture Approach**

The central thesis of the Product.ai architecture is that no single processing model is sufficient for the diverse range of interactions in e-commerce. A query for "best deals on 4K monitors" demands a low-latency, high-throughput response, while a request to "notify me when this laptop drops by 15%" requires a persistent, fault-tolerant process that may last for weeks. Our solution is a dual-architecture system, governed by an intelligent router, that directs each user request to the most appropriate engine.

The two core engines are:
1.  **The Real-Time Multi-Agent System:** Optimized for synchronous, conversational turns.
2.  **The Durable Workflow Engine:** Optimized for asynchronous, long-running, and stateful tasks.

Both engines are supported by a common set of **Core Services**, including a thread-safe Agent Registry, a Knowledge Integrator for accessing ShopGraph, and a Personalization Engine.

#### **2.1. The Real-Time Multi-Agent System**

This engine is the system's frontline, designed to handle the majority of conversational interactions with speed and accuracy. It is built around a central `DynamicOrchestrator` that implements a version of the ReAct cognitive cycle.

**Algorithm 1: Dynamic Orchestrator ReAct Cycle**
```
1. function ProcessQuery(userInput, conversationContext):
2.     Initialize thought_process = "User asked: " + userInput
3.     max_iterations = 5
4.     
5.     for i in 1...max_iterations:
6.         // REASON
7.         prompt = build_reasoning_prompt(userInput, conversationContext, thought_process)
8.         llm_reasoning = LLM.generate(prompt)
9.         thought_process += "\nThought: " + llm_reasoning.thought
10.
11.         // ACT
12.         action = llm_reasoning.action // e.g., "use_tool", "ask_user", "final_answer"
13.         tool_name = llm_reasoning.tool_name
14.         tool_input = llm_reasoning.tool_input
15.
16.         if action == "final_answer":
17.             return llm_reasoning.response
18.         
19.         if action == "use_tool":
20.             agent = AgentRegistry.get_agent_for_tool(tool_name)
21.             tool_output = agent.execute_tool(tool_name, tool_input)
22.             thought_process += "\nObservation: " + format(tool_output)
23.         
24.         else if action == "ask_user":
25.             return llm_reasoning.clarification_question
26.
27.     return "I seem to be stuck in a loop. Could you please rephrase your request?"
```
The "thinking step" is crucial. After each tool execution (line 22), the orchestrator re-evaluates the entire conversational history and the new observation. This allows it to recover from errors, handle ambiguous tool outputs, and chain tools together in novel combinations. For example, if a `ProductDiscoveryAgent` returns a list of products, the orchestrator can reason that it now needs to use the `PriceAnalysisAgent` on that list.

#### **2.2. Agent Design and Tooling**

Agents are specialized, stateless Python classes registered with the `AgentRegistry`. Each agent exposes one or more tools. A key innovation is the inclusion of code generation as a first-class tool.

*   **`codegen_fast`**: Uses a smaller, cheaper model (e.g., GPT-4o-mini) for simple, low-ambiguity calculations (e.g., applying a discount).
*   **`codegen_slow`**: Uses a powerful model (e.g., GPT-4-Turbo) for complex calculations or data transformations that require deeper reasoning, such as calculating a custom "value score" across a list of disparate products.

This tiered approach to code generation forms a "latency ladder," allowing the system to optimize for both cost and performance by using the least powerful tool necessary for a given task.

#### **2.3. The Durable Workflow Engine**

While the real-time engine excels at synchronous tasks, it is fundamentally stateless and ill-suited for processes that must survive deployments, server restarts, or last for extended periods. For these use cases, the orchestrator delegates to the Durable Workflow Engine, which is implemented using Temporal.io.

Temporal is an open-source, durable execution system that guarantees the completion of a workflow once it has started. This is achieved by persistently logging every event and state change, allowing the workflow to be rehydrated and resumed on any available worker node in the event of a failure. This provides the "exactly once" semantics critical for high-value, long-term customer interactions.

In our architecture, a workflow is a Python function decorated with `@workflow.run`. These workflows can orchestrate the same agent tools used by the real-time system, but they do so in a persistent, stateful, and fault-tolerant manner.

**Use Case: Price Monitoring Subscription**

A user request like, "Watch this laptop and buy it for me if the price drops by 20% in the next month," is impossible for a standard chatbot to handle. The orchestrator router identifies this as a durable task and initiates the `PriceWatchAndPurchaseWorkflow`.

**Algorithm 2: PriceWatchAndPurchaseWorkflow (Conceptual)**
```
1. @workflow.run
2. async function PriceWatchAndPurchaseWorkflow(product_id, target_discount, user_id):
3.     // State is automatically persisted by Temporal
4.     initial_price = await activities.get_price(product_id)
5.     target_price = initial_price * (1 - target_discount)
6.     
7.     // Workflow can sleep for long durations without consuming resources
8.     // The sleep is durable and will survive worker restarts.
9.     is_price_met = await workflow.wait_for(
10.        lambda: activities.get_price(product_id) <= target_price,
11.        timeout=timedelta(days=30)
12.    )
13.
14.    if is_price_met:
15.        // Execute a durable activity to make the purchase
16.        purchase_result = await activities.execute_purchase(user_id, product_id)
17.        await activities.send_notification(user_id, f"Success! Purchased {product_id}.")
18.        return purchase_result
19.    else:
20.        await activities.send_notification(user_id, f"Sorry, the price for {product_id} did not drop.")
21.        return "TIMEOUT"
```
This durable execution model unlocks entirely new, high-margin product offerings that are impossible for our competitors to replicate with their stateless architectures, thus creating a powerful business and technical moat.

---

### **3. Scalability and Production Considerations**

The Product.ai system was designed from the ground up for enterprise-level scale, anticipating the massive traffic surges common in e-commerce, such as on Black Friday. Our scalability strategy is multi-faceted, addressing concurrency, data volume, and system resilience.

*   **Horizontal Scalability and Concurrency:** The entire system is built on an asynchronous (asyncio) Python stack. The real-time multi-agent system is stateless, allowing it to be horizontally scaled by simply adding more container instances behind a load balancer. This enables the system to handle thousands of concurrent user sessions on a single node and scale linearly with traffic.

*   **Distributed State Management:** While the agents are stateless, the conversation is not. We use Redis as a high-throughput, distributed cache for storing conversation history, user profiles, and session context. This centralized state store ensures that any available worker can handle a user's request, preventing the need for "sticky sessions" and creating a more resilient and scalable architecture.

*   **Resilience and Graceful Degradation:** The system is designed to be resilient to partial failures. We implement the circuit breaker pattern, where the orchestrator can detect when a downstream service (e.g., a specific agent or an external API) is failing or timing out. Instead of a cascading failure, the orchestrator can reroute the query or respond to the user with a gracefully degraded message. For extreme scenarios, a `handle_black_friday_surge` mode can be activated, which intentionally disables non-essential, resource-intensive features (like `codegen_slow`) to preserve the core user experience under heavy load.

*   **Caching Strategy:** To manage data volume and reduce latency, we employ a multi-layered caching strategy in Redis. Volatile data, such as real-time product prices and inventory, is cached with a short Time-to-Live (TTL) of a few minutes. More stable data, like detailed product specifications from ShopGraph or user profiles, is cached for much longer periods. This approach minimizes redundant calls to backend services and external APIs, dramatically reducing operational costs and improving response times.

---

### **4. Evaluation and Measurement Pipeline**

A key challenge for any generative AI system is ensuring the quality, accuracy, and helpfulness of its responses. Traditional metrics like BLEU or ROUGE are insufficient for evaluating complex, task-oriented dialogue. To address this, we designed an evaluation pipeline based on the emerging state-of-the-art **LLM-as-a-Judge** paradigm (Gu et al., 2024).

The core idea is to use a powerful, independent LLM (the "Judge") to evaluate the quality of a conversation between a user and the Product.ai system. This provides a scalable and cost-effective alternative to manual human evaluation.

#### **4.1. The LLM-as-a-Judge Framework**

Our evaluation pipeline runs nightly against a curated "golden dataset" of challenging e-commerce queries. For each conversation, the Judge LLM is prompted to provide a score and a rationale across several key metrics.

**Key Metrics:**

*   **Correctness:** (Scale 1-5) Does the response contain factually accurate information? (e.g., Is the price correct? Are the product specifications valid?). This is critical for building user trust.
*   **Completeness:** (Scale 1-5) Does the response fully address all explicit and implicit parts of the user's query?
*   **Helpfulness:** (Scale 1-5) How well does the response help the user achieve their goal? This is our "North Star" metric, as it directly correlates with user satisfaction and conversion.
*   **Tool Use Accuracy:** (Binary) Did the system use the correct tool for the given step? (e.g., Did it use `codegen_fast` for simple math instead of the expensive `codegen_slow`?). This measures the efficiency of the reasoning engine.

#### **4.2. Mitigating Judge Bias**

The literature shows that LLM judges can be susceptible to biases, such as positional bias (favoring the first response it sees) or self-preference bias (favoring responses generated by its own model family). To mitigate this, we incorporate several best practices (Guerdan et al., 2025):

1.  **Multi-Judge Consensus:** We use multiple Judge LLMs from different providers (e.g., a model from Anthropic and one from Google) and compare their scores to identify outliers and establish a consensus.
2.  **Order Randomization:** For pairwise comparisons (e.g., comparing two different response strategies), we run the evaluation twice, swapping the order of the responses in the second run to cancel out positional bias.
3.  **Quantitative Regression:** We use a small set of human-rated examples to train a simple regression model that calibrates the LLM judge's scores, aligning them more closely with human judgments (Sahoo et al., 2025).

This robust evaluation framework allows us to continuously monitor and improve the quality of our system, detect performance regressions, and objectively measure the impact of new features and agents.

---

### **5. Limitations and Future Work**

While the Product.ai architecture represents a significant step forward, it is not without limitations. Acknowledging these constraints is key to defining a clear and ambitious roadmap for future development.

#### **5.1. Current Limitations**

*   **Cold Start Personalization:** While the system can build a user profile over a session, it currently lacks a sophisticated mechanism for handling the "cold start" problem for brand new users. Initial recommendations are based on query semantics alone, without the rich context of a long-term user profile.
*   **Modality Constraints:** The system is currently text-only. It cannot process or respond with images, videos, or other modalities, which are increasingly important in the e-commerce discovery process.
*   **Static Agent Registry:** The agent registry, while thread-safe and modular, is currently static. New agents can only be added through a code deployment. A truly dynamic system would allow for new agents to be registered, versioned, and deployed at runtime.
*   **Reasoning Latency:** The "thinking step" in the ReAct cycle, while powerful, introduces latency. Each reasoning step requires a round-trip to a powerful LLM, which can slow down the conversation, particularly for complex, multi-step queries.

#### **5.2. Future Roadmap and Vision**

Our future work is focused on addressing these limitations and expanding the platform's strategic capabilities.

*   **Advanced Personalization Engine:** We plan to implement a dedicated `PersonalizationEngine` that addresses the cold-start problem through progressive profiling and uses online machine learning models to update user preferences in real-time based on both explicit and implicit signals (e.g., time spent viewing a product, scroll depth).

*   **Multi-Modal Agents:** We will extend our agent framework to support multi-modal inputs and outputs. This will enable powerful new use cases, such as allowing a user to upload a picture of a product to find similar items or having the system respond with a video demonstrating a product's features.

*   **Dynamic, Versioned Agent Marketplace:** Our long-term vision is to transform the agent registry into an internal "marketplace" where teams across the company can develop, version, and deploy their own specialized agents onto the platform. This would be governed by a robust API and SDK, turning Product.ai into a true platform for conversational intelligence at Demand.io.

*   **Integration with Model-Controller-Planner (MCP) Architectures:** The modular design of Product.ai, with its clear separation of concerns, makes it perfectly suited for future integration into emerging MCP architectures. In such a paradigm, a master "Planner" LLM could delegate a high-level goal like "help me set up my new home office" to Product.ai. Our system would act as the expert "Controller" for all e-commerce related sub-tasks, seamlessly integrating its specialized knowledge and durable execution capabilities into a broader AI ecosystem. This strategic positioning ensures that our system is not just a standalone application, but a high-value, future-proof component in the next generation of AI.

---

### **6. Conclusion**

Product.ai presents a comprehensive, production-ready architecture for a new generation of conversational shopping assistants. By moving beyond monolithic LLMs and embracing a dual-architecture system that combines real-time multi-agent orchestration with durable, stateful workflows, we can address the full spectrum of user needs in a way that is robust, scalable, and intelligent. The system's ability to reason, use tools like on-demand code generation, and leverage a proprietary knowledge graph creates a deep, defensible moat. Paired with a state-of-the-art evaluation framework, Product.ai is not just a technological solution but a strategic platform poised to redefine the future of e-commerce by transforming transactions into meaningful, value-driven conversations.

---

### **7. References**

Brown, T. B., et al. (2020). Language Models are Few-Shot Learners. *arXiv preprint arXiv:2005.14165*.

Guerdan, L., et al. (2025). Validating LLM-as-a-Judge Systems in the Absence of Gold Labels. *arXiv preprint arXiv:2503.05965*.

Gu, J., et al. (2024). A Survey on LLM-as-a-Judge. *arXiv preprint arXiv:2411.15594*.

Sahoo, A., et al. (2025). Quantitative LLM Judges. *arXiv preprint arXiv:2506.02945*.

Sapkota, S., et al. (2025). Multi-Party Conversational Agents: A Survey. *arXiv preprint arXiv:2505.18845*.

Vaswani, A., et al. (2017). Attention is All You Need. *Advances in Neural Information Processing Systems, 30*.

Weizenbaum, J. (1966). ELIZA—a computer program for the study of natural language communication between man and machine. *Communications of the ACM, 9*(1), 36-45.

Yao, S., et al. (2022). ReAct: Synergizing Reasoning and Acting in Language Models. *arXiv preprint arXiv:2210.03629*. 