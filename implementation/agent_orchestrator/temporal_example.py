#!/usr/bin/env python3
"""
Temporal.io Shopping Assistant Example
Demonstrates workflow-based shopping assistance with durable, long-running processes.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.models import ConversationContext
from src.workflow_models import UserDecisionSignal

# Check if Temporal is available
try:
    from src.temporal_orchestrator import TemporalOrchestrator
    from src.orchestrator import Orchestrator
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    print("❌ Temporal.io not available. Please install temporalio package.")
    print("Run: pip install temporalio grpcio protobuf")
    sys.exit(1)

async def demonstrate_temporal_features():
    """Demonstrate Temporal.io workflow features."""
    print("🌊 " + "="*80)
    print("🌊 TEMPORAL.IO SHOPPING ASSISTANT WORKFLOW DEMONSTRATION")
    print("🌊 " + "="*80)
    
    # Initialize orchestrator in Temporal mode
    orchestrator = Orchestrator(mode="temporal")
    
    print("\n🔧 Initializing Temporal orchestrator...")
    await orchestrator.initialize()
    
    # Check system health
    print("\n💊 Health Check:")
    health = await orchestrator.health_check()
    for key, value in health.items():
        status_emoji = "✅" if "healthy" in str(value).lower() or value is True else "⚠️"
        print(f"   {status_emoji} {key}: {value}")
    
    if not health.get("temporal_connected"):
        print("\n⚠️  Temporal server not connected. Ensure Temporal is running:")
        print("   1. Start Temporal with Docker: docker-compose up -d")
        print("   2. Or install and run Temporal CLI: temporal server start-dev")
        print("   3. Temporal UI available at: http://localhost:8080")
        print("\n🔄 Falling back to enhanced orchestrator for demonstration...")
        
        # Fall back to enhanced mode for demo
        orchestrator = Orchestrator(mode="enhanced")
        await demonstrate_enhanced_features(orchestrator)
        return
    
    print(f"\n🎯 Active Mode: {orchestrator.active_mode}")
    print("🌐 Temporal UI: http://localhost:8080")
    print("📊 Monitor workflows in real-time via Temporal Web UI")
    
    # Demo contexts
    contexts = {
        "quick": ConversationContext(session_id="quick_demo", user_id="demo_user"),
        "journey": ConversationContext(session_id="journey_demo", user_id="demo_user"),
        "monitor": ConversationContext(session_id="monitor_demo", user_id="demo_user")
    }
    
    # Demo 1: Quick Query Workflow
    print("\n" + "🚀 DEMO 1: Quick Query Workflow")
    print("─" * 50)
    print("Query: 'Find gaming laptops under $1500'")
    
    response = await orchestrator.process_query(
        "Find gaming laptops under $1500",
        contexts["quick"],
        workflow_type="quick"
    )
    
    print(f"✅ Response: {response.content[:100]}...")
    print(f"🤖 Agent: {response.agent_id}")
    print(f"📊 Confidence: {response.confidence}")
    if "workflow_id" in response.data:
        print(f"🔄 Workflow ID: {response.data['workflow_id']}")
    
    # Demo 2: Shopping Journey Workflow
    print("\n" + "🛍️ DEMO 2: Comprehensive Shopping Journey Workflow")
    print("─" * 50)
    print("Query: 'Help me choose the best laptop for video editing'")
    
    journey_response = await orchestrator.start_shopping_journey(
        "Help me choose the best laptop for video editing",
        contexts["journey"]
    )
    
    print(f"✅ Journey Started: {journey_response.content[:100]}...")
    print(f"🆔 Journey ID: {journey_response.data.get('workflow_id', 'N/A')}")
    print(f"📊 Confidence: {journey_response.confidence}")
    print(f"🎯 Status: {journey_response.data.get('status', 'N/A')}")
    
    journey_id = journey_response.data.get('workflow_id')
    
    # Demo 3: Price Monitoring Workflow
    print("\n" + "💰 DEMO 3: Price Monitoring Workflow")
    print("─" * 50)
    print("Query: 'Monitor prices for MacBook Pro and alert me when they drop'")
    
    monitor_response = await orchestrator.start_price_monitoring(
        "Monitor prices for MacBook Pro and alert me when they drop",
        contexts["monitor"]
    )
    
    print(f"✅ Monitoring Started: {monitor_response.content[:100]}...")
    print(f"🆔 Monitor ID: {monitor_response.data.get('workflow_id', 'N/A')}")
    print(f"📊 Duration: {monitor_response.data.get('duration_days', 'N/A')} days")
    print(f"🔔 Product Count: {len(monitor_response.data.get('product_ids', []))}")
    
    # Demo 4: Workflow Management
    print("\n" + "⚙️ DEMO 4: Workflow Management")
    print("─" * 50)
    
    # List active workflows
    active_workflows = await orchestrator.get_active_workflows()
    print(f"📋 Active Workflows: {len(active_workflows)}")
    
    for workflow in active_workflows:
        print(f"   🔄 {workflow.get('workflow_id', 'Unknown')}")
        print(f"   📊 Status: {workflow.get('status', 'Unknown')}")
        print(f"   ⏰ Started: {workflow.get('start_time', 'Unknown')}")
        print()
    
    # Demo 5: User Decision Signal (if we have a journey)
    if journey_id and journey_response.data.get('can_receive_signals'):
        print("📤 DEMO 5: User Decision Signal")
        print("─" * 50)
        print("Simulating user decision: 'I want to postpone the purchase'")
        
        decision_data = {
            "decision_type": "postpone",
            "reasoning": "Need to think about it more"
        }
        
        signal_sent = await orchestrator.send_workflow_signal(journey_id, decision_data)
        
        if signal_sent:
            print("✅ Decision signal sent successfully")
            print("🔄 This would trigger price monitoring for selected products")
        else:
            print("❌ Failed to send decision signal")
    
    # Demo 6: Workflow Query Processing
    print("\n" + "🤖 DEMO 6: Intelligent Workflow Selection")
    print("─" * 50)
    
    test_queries = [
        ("Find cheap headphones", "Should trigger: Quick workflow"),
        ("Help me decide between iPhone and Samsung", "Should trigger: Journey workflow"),
        ("Watch for price drops on gaming chairs", "Should trigger: Monitor workflow"),
        ("Compare laptop vs desktop pros and cons", "Should trigger: Journey workflow")
    ]
    
    for query, expected in test_queries:
        print(f"Query: '{query}'")
        print(f"Expected: {expected}")
        
        response = await orchestrator.process_query(
            query,
            ConversationContext(session_id=f"test_{hash(query)}", user_id="demo_user")
        )
        
        workflow_type = "Unknown"
        if "temporal" in response.agent_id:
            if "journey" in response.agent_id:
                workflow_type = "Journey"
            elif "monitor" in response.agent_id:
                workflow_type = "Monitor"
            else:
                workflow_type = "Quick"
        elif "workflow" in response.data.get("processed_by", ""):
            workflow_type = "Quick"
        
        print(f"✅ Actual: {workflow_type} workflow")
        print(f"🤖 Agent: {response.agent_id}")
        print()
    
    # Demo 7: Workflow Status and Monitoring
    print("📊 DEMO 7: Workflow Status Monitoring")
    print("─" * 50)
    
    if active_workflows:
        for workflow in active_workflows[:2]:  # Show first 2 workflows
            workflow_id = workflow.get('workflow_id')
            if workflow_id:
                status = await orchestrator.temporal_orchestrator.get_workflow_status(workflow_id)
                if status:
                    print(f"🔄 Workflow: {workflow_id}")
                    print(f"   📊 Status: {status.get('status', 'Unknown')}")
                    print(f"   ⏰ Runtime: {status.get('execution_time', 'Unknown')}")
                    print(f"   📈 Events: {status.get('history_length', 0)}")
                    print()
    
    # Cleanup
    print("🧹 DEMO 8: Cleanup and Resource Management")
    print("─" * 50)
    print("Cleaning up orchestrator resources...")
    
    await orchestrator.cleanup()
    print("✅ Cleanup completed")
    
    print("\n" + "🎯 TEMPORAL.IO FEATURES DEMONSTRATED:")
    print("✅ Durable workflow execution")
    print("✅ Long-running price monitoring")
    print("✅ Interactive shopping journeys")
    print("✅ Workflow state management")
    print("✅ Signal-based user interaction")
    print("✅ Automatic workflow selection")
    print("✅ Fault tolerance and recovery")
    print("✅ Real-time monitoring and observability")

async def demonstrate_enhanced_features(orchestrator):
    """Fallback demonstration using enhanced orchestrator."""
    print("\n🚀 Enhanced Orchestrator Demo (Temporal fallback)")
    print("─" * 50)
    
    context = ConversationContext(session_id="enhanced_demo", user_id="demo_user")
    
    queries = [
        "Find gaming laptops",
        "What's the price of MacBook Pro?",
        "Show me deals on headphones"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        response = await orchestrator.process_query(query, context)
        print(f"✅ Response: {response.content[:100]}...")
        print(f"🤖 Agent: {response.agent_id}")
        print(f"📊 Confidence: {response.confidence}")

async def start_temporal_server_instructions():
    """Provide instructions for starting Temporal server."""
    print("🐳 " + "="*80)
    print("🐳 TEMPORAL SERVER SETUP INSTRUCTIONS")
    print("🐳 " + "="*80)
    
    print("\n📋 Option 1: Docker Compose (Recommended)")
    print("─" * 50)
    print("1. Run: docker-compose up -d")
    print("2. Wait for services to start (~30 seconds)")
    print("3. Access Temporal UI: http://localhost:8080")
    print("4. Re-run this example")
    
    print("\n📋 Option 2: Temporal CLI")
    print("─" * 50)
    print("1. Install: brew install temporal")
    print("2. Run: temporal server start-dev")
    print("3. Access Temporal UI: http://localhost:8080")
    print("4. Re-run this example")
    
    print("\n📋 Option 3: Run Without Temporal")
    print("─" * 50)
    print("The example will automatically fallback to enhanced orchestrator")
    print("You'll still see agent-based processing without workflow features")

async def main():
    """Main demonstration function."""
    print("🛍️ Product.ai Shopping Assistant - Temporal.io Edition")
    print("=" * 80)
    
    if not TEMPORAL_AVAILABLE:
        print("❌ Temporal.io SDK not available")
        return
    
    try:
        await demonstrate_temporal_features()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo interrupted by user")
        
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        print("\n📋 If Temporal server is not running:")
        await start_temporal_server_instructions()
        
    finally:
        print("\n👋 Demo completed! Thank you for exploring Temporal.io workflows!")
        print("\n🌐 Resources:")
        print("   • Temporal Documentation: https://docs.temporal.io/")
        print("   • Temporal UI: http://localhost:8080 (when running)")
        print("   • Project Architecture: ./architecture/system-design.md")

if __name__ == "__main__":
    asyncio.run(main()) 