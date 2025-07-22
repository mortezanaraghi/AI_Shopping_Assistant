Design the technical architecture for Product.ai - our AI shopping assistant that delivers expert-level guidance comparable to human product specialists. Unlike generic AI chatbots, this system must orchestrate specialized agents while effectively leveraging our ShopGraph knowledge to provide genuinely helpful shopping advice.
Expectations:
Architecture (Section 1): Design the COMPLETE system showing how agent orchestration, knowledge integration, AND personalization work together
Implementation (Section 2): Code ONE component deeply to demonstrate your expertise
Presentations: Create a cohesive technical narrative that starts at 10,000 feet and progressively zooms into implementation details
Time: 8 hours total - prioritize showing both breadth (full system) and depth (one component)
Example Target Experience:
User: "I need a laptop for video editing under $2000"

System should intelligently guide users through complex purchasing decisions with:
- Expert-level product knowledge and recommendations
- Natural conversation flow with context retention
- Proactive clarifying questions about specific use cases
- Detailed product comparisons with reasoning
- Real-time pricing and availability information


Business Context: Our Competitive Advantage
ShopGraph Knowledge: Our proprietary graph contains 400,000+ merchants, millions of products, and complex relationships (compatibility, alternatives, bundles) that no competitor can match.
Technical Challenge: How do you architect a system that turns this structured knowledge into conversational shopping expertise that's demonstrably better than Google Shopping AI, Amazon Rufus, or Perplexity Shopping?
Your Deliverables
1. System Architecture Design (3 hours)
Create comprehensive architecture documentation including:
High-Level Architecture
System architecture diagram showing agent coordination
Component responsibilities and interaction patterns
Integration points with ShopGraph and external systems
Technology stack decisions with justifications
Core Components Design (REQUIRED - Address All Three)
You must explain how ALL three components work together in your architecture:
Agent Orchestration Engine: How agents coordinate to handle complex queries
ShopGraph Knowledge Integration: How structured data enhances conversations
Personalization & Recommendations: How the system learns and adapts to users
Note: You'll implement ONE in detail in Section 2, but your architecture must show how all three integrate.
Agent Design Philosophy
Specifications for 3-4 key specialized agents
Agent communication patterns and coordination mechanisms
How agents share context and maintain conversation coherence
Failure handling and fallback strategies
Data Architecture
How structured product knowledge integrates with LLM capabilities
Real-time data handling (pricing, inventory, recommendations)
Conversation state management and context retention
Performance optimization strategies (caching, indexing, etc.)
Competitive Differentiation
Brief comparison to existing solutions (Google Shopping AI, Amazon, Perplexity)
How ShopGraph integration creates unique value
Technical moats that are hard to replicate
2. Key Component Implementation (3 hours)
IMPORTANT: While you implement ONE component below, your architecture document must explain how ALL THREE components work together. During the presentations, you'll discuss all components conceptually before diving deep into your implementation.
Implementation Philosophy: Focus on demonstrating deep expertise in your chosen component. We're not looking for a full system implementation—we want to see robust, well-engineered code that shows you understand production concerns like error handling, scaling, and system integration. Use comments to explain approaches where full implementation isn't feasible within time constraints.
Choose ONE component to implement in detail (demonstrates your technical depth):
Option A: Agent Orchestration Engine
class AgentOrchestrator:
    """Central coordinator for all shopping assistant agents"""
    def __init__(self, agents: Dict[str, Agent]):
        self.agents = agents
        self.conversation_state = ConversationState()

    async def process_query(self, user_input: str, context: ConversationContext) -> AgentResponse:
        """
        Coordinate multiple agents to generate expert shopping guidance
        Requirements: agent selection logic, context sharing, failure handling
        """
        pass

    async def route_to_agents(self, query: ParsedQuery) -> List[AgentTask]:
        """
        Determine which agents to involve and in what order
        Requirements: dependency management, parallel vs sequential execution
        """
        pass

    def handle_black_friday_surge(self, scale_factor: int = 50) -> ScalingStrategy:
        """
        Handle 50x traffic surge scenarios
        Requirements: degradation strategy, priority queuing, cache optimization
        """
        pass



External Dependencies to Mock:
Individual agent implementations
LLM API calls (OpenAI, Claude, etc.) - you can mock a generic LLM handler without diving into any specifics
Message queue/coordination service
Conversation state storage
Option B: ShopGraph Knowledge Integration
class KnowledgeIntegrator:
    """Transforms structured product data into conversational insights"""
    def __init__(self, shopgraph_api: ShopGraphAPI):
        self.shopgraph = shopgraph_api
        self.cache = KnowledgeCache()

    async def get_expert_recommendations(self, requirements: UserRequirements) -> List[ProductRecommendation]:
        """
        Combine structured knowledge with LLM reasoning for expert advice
        Requirements: graph traversal, ranking algorithms, explanation generation
        """
        pass

    async def handle_incomplete_data(self, products: List[Product]) -> EnrichedProducts:
        """
        Handle missing or conflicting product information
        Requirements: data quality scoring, inference strategies, confidence levels
        """
        pass

    def create_unique_insights(self, product_graph: GraphData) -> List[Insight]:
        """
        Generate insights only possible with ShopGraph's relationship data
        Requirements: cross-product patterns, compatibility analysis, hidden gems
        """
        pass



External Dependencies to Mock:
ShopGraph API (product data, relationships, merchant info)
Vector database for similarity search
LLM for generating explanations
Cache layer (Redis or similar)
Option C: Personalization & Recommendation Engine
class PersonalizationEngine:
    """ML-powered personalization for shopping recommendations"""

    def __init__(self):
        self.user_embeddings = UserEmbeddingModel()
        self.product_vectors = ProductVectorStore()
        self.exploration_policy = ExplorationPolicy()

    async def handle_cold_start(self, initial_query: str, session_context: SessionContext) -> UserProfile:
        """
        Address cold start problem for new users
        Requirements: progressive profiling, transfer learning, smart defaults
        """
        pass

    async def real_time_preference_learning(self, interaction: UserInteraction) -> UpdatedProfile:
        """
        Update preferences in real-time based on conversation signals
        Requirements: online learning, implicit feedback, embedding updates
        """
        pass

    async def exploration_exploitation_balance(self, user_state: UserState, candidates: List[Product]) -> RankedProducts:
        """
        Balance showing best matches vs discovering preferences
        Requirements: multi-armed bandits, diversity injection, uncertainty sampling
        """
        pass



External Dependencies to Mock:
Embedding model/service
Vector store (Pinecone, Weaviate, etc.)
User profile storage
Product catalog
Feature extraction pipeline
Implementation Requirements
Language: Python strongly preferred (3.9+), but we'll consider exceptional implementations in TypeScript/Go if that better demonstrates your expertise
Runnable Code: Must be executable with clear setup instructions
Mocked Dependencies: Use fixtures/mocks for external services (ShopGraph API, LLMs, etc.)
Example Usage: Include a main.py or similar that demonstrates your component in action
Test Suite: At least 3 unit tests that can be run with pytest or similar
Environment: Use requirements.txt or poetry.lock for Python (or appropriate dependency management for other languages)
Documentation:
README with setup and run instructions
Inline code comments explaining complex logic
One Architecture Decision Record (ADR) for a major choice
Code Structure Example
your-component/
├── README.md              # Setup, run instructions, design decisions
├── requirements.txt       # Dependencies (or pyproject.toml for poetry)
├── src/
│   ├── __init__.py
│   ├── your_component.py  # Main implementation
│   └── models.py          # Data models/types
├── tests/
│   ├── __init__.py
│   └── test_component.py  # Unit tests
├── fixtures/
│   ├── shopgraph_mock.py  # Mock ShopGraph responses
│   └── sample_data.json   # Test data
├── example.py             # Runnable demo showing your component
└── docs/
    └── adr-001-component-choice.md  # Why you chose this component



What We'll Test



# We should be able to run:
pip install -r requirements.txt
python -m pytest tests/
python example.py

# And see your component handle scenarios like:
# - Normal operation
# - Error cases
# - Performance under load
# - Integration with mocked services



Example Demo Script
Your example.py should demonstrate:
# example.py
"""
Demo of the PersonalizationEngine (or your chosen component)
Shows: cold start handling, preference learning, recommendations
"""

async def main():
    # Initialize with mocked dependencies
    engine = PersonalizationEngine(
        embedding_model=MockEmbeddingModel(),
        vector_store=MockVectorStore(),
        product_catalog=MockProductCatalog()
    )

    # Scenario 1: New user (cold start)
    print("=== Cold Start Scenario ===")
    user_profile = await engine.handle_cold_start(
        "I need a laptop for video editing",
        SessionContext(device="mobile", location="US")
    )

    # Scenario 2: Learning from interaction
    print("\\n=== Preference Learning ===")
    interaction = UserInteraction(
        liked_product_id="laptop_123",
        time_spent=45.2,
        asked_about=["RAM", "GPU"]
    )
    updated_profile = await engine.real_time_preference_learning(interaction)

    # Scenario 3: Get recommendations
    print("\\n=== Recommendations ===")
    recommendations = await engine.exploration_exploitation_balance(
        user_state=updated_profile,
        candidates=mock_products
    )

    # Show results
    for i, rec in enumerate(recommendations[:5]):
        print(f"{i+1}. {rec.name} - Score: {rec.score:.2f}")

if __name__ == "__main__":
    asyncio.run(main())



3. Evaluation & Improvement Framework (1.5 hours)
Design a system for continuous improvement and quality measurement:
class EvaluationPipeline:
    """Automated evaluation and improvement system"""

    async def measure_conversation_quality(self, conversation: Conversation) -> QualityMetrics:
        """
        Measure expert-level guidance quality
        Define: What makes a conversation "expert-level"?
        Metrics: Beyond simple completion rates
        """
        pass

    async def detect_model_drift(self, predictions: List[Prediction], outcomes: List[Outcome]) -> DriftAnalysis:
        """
        Detect when system performance degrades
        Requirements: Statistical tests, drift types, alert thresholds
        """
        pass

    async def identify_improvement_opportunities(self, failed_patterns: List[Pattern]) -> ImprovementPlan:
        """
        Transform failures into system improvements
        Requirements: Error taxonomy, prioritization, automated fixes
        """
        pass



Key Questions to Address
How do you prove the system provides "expert-level" guidance?
What metrics indicate an agent is underperforming before users complain?
How do you maximize learning from minimal human review time?
4. Platform Strategy & Technical Roadmap (0.5 hours)
Brief documentation covering:
Platform Extensibility
How other teams add new shopping domains
API design for internal teams to build on your platform
Abstraction layers hiding complexity while maintaining flexibility
Evolution Strategy
From electronics to fashion/home/beauty
Framework for adding new agent capabilities
Network effects and data moats over time
How You'll Present Your Work
You'll participate in a two-part technical presentation that flows from high-level overview to deep technical exploration.
Presentation Format: Prepare slides or a detailed outline that supports a continuous narrative—you'll share your screen during the presentations. Think of this as one extended technical discussion that progressively zooms in on details.
Part 1: Technical Overview & Solution Walkthrough (45 minutes)
Audience: Broader team including founder, product, and engineering
Start by explaining the assignment itself (5 min):
Brief overview of the challenge requirements
What you were asked to build and why
Key constraints and considerations
Present your solution at a technical but accessible level (25 min):
System Architecture (10 min): How your complete system works
Component Integration (10 min): How orchestration, knowledge, and personalization work together
Business Impact (5 min): How this creates competitive advantage
Initial Q&A and Discussion (15 min):
Technical questions at a high level
Business alignment and strategic considerations
Setting up topics for deeper exploration in Part 2
Key Points to Cover
Walk through a user query end-to-end showing how components interact
Explain your technology choices in business terms
Highlight what makes this approach unique vs competitors
Address scalability and extensibility
Part 2: Deep Technical Dive (1.5+ hours)
Continues with technical team members
This flows naturally from Part 1 - progressively zooming into implementation details:
Architecture Deep Dive (20 min): Detailed technical decisions and trade-offs
Implemented Component Walkthrough (30 min): Line-by-line code review of your chosen component
Production Considerations (20 min): Scaling, monitoring, failure modes
Extended Technical Discussion (20+ min): Complex scenarios and edge cases
Technical Topics to Explore
Walk through your code implementation in detail
Discuss specific technical challenges and solutions
Deep dive into the Black Friday 50x surge scenario
Explore integration patterns and system boundaries
Discuss testing strategies and quality assurance
Review monitoring and observability approach
Note: Part 2 often extends beyond scheduled time as we explore interesting technical topics. We'll follow the conversation where it leads naturally.
Evaluation Criteria
Architecture Quality (35%)
Complete system design showing integration of ALL core components
Sophisticated multi-agent coordination that scales
Effective ShopGraph integration creating unique value
Production-ready design with clear failure modes
Justified technical decisions and trade-offs
Implementation Depth (30%)
High-quality code demonstrating technical expertise
Well-designed interfaces enabling platform thinking
Proper error handling and testing
Clean, maintainable implementation
Clear rationale for why you chose this component to implement
Technical Communication (25%)
Ability to explain complex systems at multiple levels of detail
Clear progression from high-level to detailed technical discussion
Thoughtful responses to technical challenges
Evidence of systematic thinking
Ability to discuss trade-offs and alternatives
System Thinking & Vision (10%)
Understanding of how all components create business value
Platform mindset enabling future expansion
Consideration of real-world constraints
Innovation balanced with pragmatism
Clear path from MVP to scale
Resources & Support
What We Provide
ShopGraph Data Schema
Available here and includes:
Product catalog structure and relationships
Merchant and pricing data format
Graph traversal examples and best practices
API interfaces and rate limits
Sample JSON responses for mocking
What You Should Mock
Since you won't have access to our actual systems, please create realistic mocks for:
ShopGraph API: Return sample product data, relationships, and merchant info
LLM Services: Simulate responses without actual API calls
Vector Stores: Use in-memory structures or simple similarity calculations
External Services: Any other dependencies your design requires
Time-Saver: Focus on mocking just enough to demonstrate your component works. For example, 10-20 sample products with basic relationships is sufficient—don't spend hours creating elaborate test data.
Example mock structure:
class MockShopGraphAPI:
    """Mock implementation for testing"""
    def __init__(self):
        self.products = load_json_fixture('sample_products.json')

    async def search_products(self, query: str) -> List[Product]:
        # Return filtered products based on query
        return [p for p in self.products if query.lower() in p.name.lower()]



Questions During Assignment
Email bri@demand.io for clarifications
We'll respond within 24 hours on weekdays
Submission Requirements
GitHub Repository (public or private with access granted to bri@demand.io)
Architecture diagrams (any format - Figma, draw.io, Excalidraw, etc.)
Presentation materials that support your continuous narrative
README with setup instructions and key decisions
Required Repository Structure
ai-technical-lead-takehome/
├── README.md                    # Overview, setup, key decisions
├── architecture/
│   ├── system-design.md         # Complete architecture document
│   ├── diagrams/               # Architecture diagrams
│   └── component-integration.md # How all components work together
├── implementation/
│   ├── [your-chosen-component]/ # Working code (see structure above)
│   ├── requirements.txt        # or pyproject.toml
│   └── README.md               # How to run your code
├── presentation/
│   └── technical-presentation.pdf  # Unified presentation materials
└── evaluation/
    └── metrics-framework.md     # Your evaluation system design



Submission Checklist
[ ] Code runs with provided instructions
[ ] Tests pass (python -m pytest)
[ ] Example demo works (python example.py)
[ ] Architecture covers ALL components
[ ] Presentation materials support continuous narrative
[ ] Repository is well-organized and documented
Success Tips
Time Management Guidance
Given the 8-hour time constraint, we recommend this allocation:
Must Have (6 hours):
Architecture covering all 3 components: 2.5 hours
One component implementation: 3 hours
Basic presentation materials: 0.5 hours
Nice to Have (2 hours):
Evaluation framework: 1 hour (can be conceptual)
Platform strategy: 0.5 hours (bullet points fine)
Polish and documentation: 0.5 hours
What We DON'T Expect:
Perfect production code (good structure > completeness)
Extensive documentation (clear README + code comments sufficient)
Polished presentations (clear outline/sketches fine)
Implementation of evaluation framework (design only)
Comprehensive test coverage (3 solid tests > 20 basic ones)
Pro tip: Strong candidates show good judgment about where to go deep. If you're running short on time, prioritize:
Clear architecture showing all components working together
Working code for your chosen component (even if not all edge cases)
Strong explanation of your design choices
We're evaluating thinking quality and technical depth, not perfect coverage. Show us how you think about the problem and make smart trade-offs with limited time.
Presentation Approach
Start with the big picture and progressively zoom in
Use consistent examples throughout to show different levels of detail
Prepare to go deep on any component, not just your implementation
Think of it as teaching us about your system, not selling it
Show Your Strengths
If you've built similar systems, reference them
If new to shopping domain, show how your expertise translates
Demonstrate systematic thinking at every level
Choose the implementation component that best showcases your skills
Be Realistic
Acknowledge trade-offs and limitations
Show iterative approach from MVP to scale
Focus on what's genuinely differentiated
Explain why you chose your specific component to implement
Remember the Complete Picture
Your architecture must show how ALL components work together
Implementation demonstrates depth in ONE area
Presentation should cover the full system, not just what you built
We want to see both forest (complete system) and trees (detailed implementation)
Final Submission Summary
✅ Architecture: Complete system design with orchestration + knowledge + personalization
✅ Code: ONE component that runs with python example.py and passes tests
✅ Presentation: Materials supporting a continuous technical narrative
✅ Documentation: Clear README, setup instructions, and design decisions
We're excited to see your vision for transforming how people discover and buy products online. This is a rare opportunity to architect something truly revolutionary in AI commerce.
