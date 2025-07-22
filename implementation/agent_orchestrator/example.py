#!/usr/bin/env python3
"""
Enhanced Product.ai Shopping Assistant Demo
Showcases the new multi-agent architecture with specialized agents.
"""
import asyncio
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.models import ConversationContext
from src.orchestrator import Orchestrator

async def demo_basic_functionality():
    """Demonstrate basic shopping assistance functionality."""
    print("🛍️  Product.ai Enhanced Shopping Assistant Demo")
    print("=" * 60)
    
    orchestrator = Orchestrator()
    
    # Check system health
    if hasattr(orchestrator, 'health_check'):
        health = await orchestrator.health_check()
        print(f"System Health: {health}")
        print()
    
    # Demo queries that showcase different agent capabilities
    demo_queries = [
        {
            "query": "I need a laptop for 4K video editing under $2000",
            "description": "Product Discovery + Price Analysis"
        },
        {
            "query": "Show me gaming laptops with good deals",
            "description": "Product Search + Deal Detection"
        },
        {
            "query": "Find budget-friendly laptops under $800",
            "description": "Budget-Focused Search"
        }
    ]
    
    for i, demo in enumerate(demo_queries, 1):
        print(f"Demo {i}: {demo['description']}")
        print(f"Query: \"{demo['query']}\"")
        print("-" * 40)
        
        # Create conversation context
        context = ConversationContext(session_id=f"demo_session_{i}")
        
        # Measure response time
        start_time = time.time()
        
        try:
            response = await orchestrator.process_query(demo['query'], context)
            
            response_time = time.time() - start_time
            
            print(f"Response ({response_time:.2f}s):")
            print(response.content)
            
            # Show agent/tool information if available
            if hasattr(response, 'agent_id') and response.agent_id:
                print(f"\nProcessed by: {response.agent_id}")
            
            if hasattr(response, 'confidence') and response.confidence is not None:
                print(f"Confidence: {response.confidence:.2f}")
            
            if response.tool_calls:
                print(f"Tools used: {', '.join(response.tool_calls)}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "=" * 60 + "\n")
        
        # Small delay between demos
        await asyncio.sleep(0.5)

async def demo_conversation_flow():
    """Demonstrate conversation flow and context management."""
    print("💬 Conversation Flow Demo")
    print("=" * 60)
    
    orchestrator = Orchestrator()
    context = ConversationContext(session_id="conversation_demo")
    
    conversation_flow = [
        "I'm looking for a laptop",
        "What about pricing for those laptops?",
        "Show me the cheapest option"
    ]
    
    for i, query in enumerate(conversation_flow, 1):
        print(f"Turn {i}: \"{query}\"")
        print("-" * 30)
        
        try:
            response = await orchestrator.process_query(query, context)
            print(f"Response: {response.content}")
            
            # Show conversation context if available
            if hasattr(orchestrator, 'state_manager'):
                try:
                    history = await orchestrator.state_manager.get_conversation_history(
                        context.session_id, limit=5
                    )
                    if history:
                        print(f"Conversation length: {len(history)} messages")
                except Exception:
                    pass  # State manager might not be fully functional
            
        except Exception as e:
            print(f"Error: {e}")
        
        print()

async def demo_agent_specialization():
    """Demonstrate agent specialization capabilities."""
    print("🤖 Agent Specialization Demo")
    print("=" * 60)
    
    orchestrator = Orchestrator()
    
    # Check if enhanced orchestrator is available
    if hasattr(orchestrator, 'agent_coordinator'):
        print("✅ Enhanced agent architecture is active!")
        
        # Show registered agents
        if hasattr(orchestrator.agent_coordinator, 'registry'):
            agents = orchestrator.agent_coordinator.registry.get_all_agents()
            print(f"Registered agents: {len(agents)}")
            for agent in agents:
                capabilities = [cap.value for cap in agent.capabilities]
                print(f"  - {agent.agent_id}: {', '.join(capabilities)}")
        
        print()
        
        # Test agent selection for different query types
        test_queries = [
            ("Find laptops", "Should trigger Product Discovery Agent"),
            ("What's the price?", "Should trigger Price Analysis Agent"),
            ("Show me deals", "Should trigger multiple agents")
        ]
        
        for query, expected in test_queries:
            print(f"Query: \"{query}\" - {expected}")
            context = ConversationContext(session_id=f"agent_test_{hash(query)}")
            
            try:
                response = await orchestrator.process_query(query, context)
                
                if hasattr(response, 'agent_id') and response.agent_id:
                    print(f"✅ Handled by: {response.agent_id}")
                else:
                    print("📝 Handled by legacy tool system")
                    
                print(f"Response: {response.content[:100]}...")
                
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print()
    else:
        print("📝 Running with legacy tool-based orchestrator")
        print("Enhanced agent architecture not available.")

async def demo_performance_features():
    """Demonstrate performance and scalability features."""
    print("⚡ Performance Features Demo")
    print("=" * 60)
    
    orchestrator = Orchestrator()
    
    # Test surge handling
    if hasattr(orchestrator, 'handle_black_friday_surge'):
        print("Testing surge handling...")
        orchestrator.handle_black_friday_surge(scale_factor=60)
        print("✅ Surge handling activated")
        print()
    
    # Test concurrent queries
    print("Testing concurrent query processing...")
    
    concurrent_queries = [
        "laptop under $1000",
        "gaming mouse deals", 
        "4K monitors on sale"
    ]
    
    tasks = []
    for i, query in enumerate(concurrent_queries):
        context = ConversationContext(session_id=f"concurrent_{i}")
        task = orchestrator.process_query(query, context)
        tasks.append(task)
    
    start_time = time.time()
    try:
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"✅ Processed {len(responses)} queries concurrently in {total_time:.2f}s")
        
        for i, response in enumerate(responses):
            print(f"  Query {i+1}: {len(response.content)} chars response")
            
    except Exception as e:
        print(f"❌ Concurrent processing error: {e}")

async def main():
    """Run all demos."""
    print("🚀 Starting Product.ai Enhanced Demo\n")
    
    try:
        await demo_basic_functionality()
        await demo_conversation_flow()
        await demo_agent_specialization()
        await demo_performance_features()
        
        print("✅ Demo completed successfully!")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nThank you for trying Product.ai! 🛍️")

if __name__ == "__main__":
    asyncio.run(main())

 