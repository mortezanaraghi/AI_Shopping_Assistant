# AI Shopping Assistant - Agent Orchestration System

A sophisticated multi-layered agent orchestration system that provides intelligent shopping assistance through multiple orchestration strategies including ReAct, Temporal workflows, and enhanced agent-based approaches.

## 🚀 Features

- **Multi-Modal Orchestration**: Supports ReAct, Temporal, Enhanced, and Legacy modes
- **Dynamic Mode Selection**: Automatically chooses the best orchestration strategy
- **Smart Termination**: Intelligent early termination to prevent unnecessary iterations
- **Tool Validation**: Comprehensive tool argument validation and schema management
- **Fault Tolerance**: Graceful fallbacks between orchestration modes
- **Observability**: Comprehensive logging and tracing with OpenTelemetry
- **Scalability**: Designed for high-throughput shopping queries

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)

## 🏗️ Architecture Overview

The system implements a sophisticated multi-layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                        │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │   ReAct     │ │  Temporal   │ │ Enhanced    │ │ Legacy  │ │
│ │Orchestrator │ │Orchestrator │ │Orchestrator │ │Orchestr.│ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 State Manager                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │Conversation │ │ User Profile│ │ Tool History│            │
│  │  History    │ │             │ │             │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Agent Framework                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Product     │ │ Price       │ │ Deal        │            │
│  │ Discovery   │ │ Analysis    │ │ Detection   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Orchestration Modes

1. **ReAct Orchestrator**: Iterative reasoning pattern for complex queries
2. **Temporal Orchestrator**: Durable workflows for long-running processes
3. **Enhanced Orchestrator**: Specialized agent-based approach
4. **Legacy Orchestrator**: Simple tool-based fallback

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from src.orchestrator import Orchestrator
from src.models import ConversationContext

async def main():
    # Create orchestrator (auto-selects best mode)
    orchestrator = Orchestrator()
    
    # Create conversation context
    context = ConversationContext(session_id="user_session_123")
    
    # Process a query
    response = await orchestrator.process_query(
        "I need a laptop for 4K video editing under $2000", 
        context
    )
    
    print(f"Response: {response.content}")
    print(f"Confidence: {response.confidence}")
    print(f"Tools used: {response.tool_calls}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Specific Mode Usage

```python
# Use ReAct mode explicitly
react_orchestrator = Orchestrator(mode="react")

# Use Temporal mode for long-running workflows
temporal_orchestrator = Orchestrator(mode="temporal")

# Use Enhanced mode for agent-based processing
enhanced_orchestrator = Orchestrator(mode="enhanced")
```

## 📦 Installation

### Prerequisites

- Python 3.9+
- OpenAI API key
- ShopGraph API key (optional)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the project root:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
SHOPGRAPH_API_KEY=your_shopgraph_api_key_here

# ReAct Configuration
REACT_MAX_ITERATIONS=5
REACT_CONFIDENCE_THRESHOLD=0.7

# Temporal Configuration (optional)
TEMPORAL_ADDRESS=localhost:7233

# Logging
LOG_LEVEL=INFO
```

## ⚙️ Configuration

### Settings

The system uses a centralized configuration system:

```python
from src.config import get_settings

settings = get_settings()

# Access configuration values
max_iterations = settings.react_max_iterations
confidence_threshold = settings.react_confidence_threshold
```

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `openai_api_key` | str | Required | OpenAI API key |
| `shopgraph_api_key` | str | Required | ShopGraph API key |
| `react_max_iterations` | int | 5 | Maximum ReAct loop iterations |
| `react_confidence_threshold` | float | 0.7 | Confidence threshold for termination |
| `temporal_address` | str | localhost:7233 | Temporal server address |
| `log_level` | str | INFO | Logging level |

## 📖 Usage Examples

### Example 1: Basic Product Search

```python
async def basic_search():
    orchestrator = Orchestrator()
    context = ConversationContext(session_id="search_1")
    
    response = await orchestrator.process_query(
        "find gaming laptops under $1500", 
        context
    )
    
    return response
```

### Example 2: Complex Analysis

```python
async def complex_analysis():
    orchestrator = Orchestrator(mode="react")
    context = ConversationContext(session_id="analysis_1")
    
    response = await orchestrator.process_query(
        "Compare these laptops for 4K video editing and recommend the best one", 
        context
    )
    
    return response
```

### Example 3: Price Monitoring

```python
async def price_monitoring():
    orchestrator = Orchestrator(mode="temporal")
    context = ConversationContext(session_id="monitor_1")
    
    response = await orchestrator.start_price_monitoring(
        "Monitor price drops for MacBook Pro", 
        context
    )
    
    return response
```

### Example 4: Shopping Journey

```python
async def shopping_journey():
    orchestrator = Orchestrator(mode="temporal")
    context = ConversationContext(session_id="journey_1")
    
    response = await orchestrator.start_shopping_journey(
        "Help me find the perfect laptop for my needs", 
        context
    )
    
    return response
```

## 🧪 Testing

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run Specific Test Categories

```bash
# ReAct orchestration tests
python -m pytest tests/test_react_orchestration.py -v

# Temporal workflow tests
python -m pytest tests/test_temporal.py -v

# Tool validation tests
python -m pytest tests/test_tool_schema_registry.py -v

# Smart termination tests
python -m pytest tests/test_smart_termination_analyzer.py -v
```

### Test Coverage

The test suite provides comprehensive coverage:

- **Total Tests**: 95 tests across 9 test files
- **Coverage Areas**: ReAct, Temporal, Enhanced, Legacy orchestration
- **Test Types**: Unit, Integration, End-to-End, Performance

### Run Demos

```bash
# Basic functionality demo
python example.py

# Temporal workflow demo
python temporal_example.py
```

## 📚 Documentation

### Architecture Documentation

- [Orchestrator Architecture](docs/ORCHESTRATOR_ARCHITECTURE.md) - Detailed architecture explanation
- [Test Coverage and Logic](docs/TEST_COVERAGE_AND_LOGIC.md) - Comprehensive test documentation

### Key Components

#### ReAct Orchestrator

The ReAct (Reason-Act) orchestrator implements an iterative reasoning pattern:

```python
# ReAct loop: Reason → Act → Observe → Repeat
while react_state.current_iteration < self.max_iterations:
    # STEP 1: REASON (The "Thinking Step")
    reasoning_result = await self._reason(react_state)
    
    # STEP 2: Check for early termination
    should_terminate, reason = self.termination_analyzer.should_terminate(
        react_state, reasoning_result
    )
    
    if should_terminate:
        break
    
    # STEP 3: ACT (The "Action Step")
    action_result = await self._act_with_validation(reasoning_result, react_state)
    
    # STEP 4: OBSERVE (The "Learning Step")
    await self._observe(action_result, react_state)
```

#### Tool Schema Registry

Centralized tool schema management with validation:

```python
# Validate tool arguments
is_valid, msg = tool_registry.validate_arguments(
    "sg_list_candidates", 
    {"query": "gaming laptops"}
)

if not is_valid:
    # Handle validation error
    pass
```

#### Smart Termination Analyzer

Intelligent termination logic to prevent unnecessary iterations:

```python
# Check termination conditions
should_terminate, reason = analyzer.should_terminate(react_state, reasoning_result)

if should_terminate:
    # Terminate early with reason
    break
```

## 🔧 Development

### Project Structure

```
src/
├── orchestrator.py              # Main orchestrator entry point
├── react_orchestrator.py        # ReAct pattern implementation
├── temporal_orchestrator.py     # Temporal workflow integration
├── enhanced_orchestrator.py     # Enhanced agent-based approach
├── tool_schema_registry.py      # Tool validation system
├── smart_termination_analyzer.py # Termination logic
├── models.py                    # Data models
├── config.py                    # Configuration management
└── tools/                       # Tool implementations
    ├── sg_list_candidates.py
    ├── sg_price_drop.py
    └── ...

tests/
├── test_react_orchestration.py
├── test_temporal.py
├── test_tool_schema_registry.py
├── test_smart_termination_analyzer.py
└── ...

docs/
├── ORCHESTRATOR_ARCHITECTURE.md
└── TEST_COVERAGE_AND_LOGIC.md
```

### Adding New Tools

1. Create tool implementation in `src/tools/`
2. Add schema to `ToolSchemaRegistry`
3. Update tests
4. Document the tool

### Adding New Orchestration Modes

1. Implement orchestrator class
2. Add to main orchestrator selection logic
3. Create comprehensive tests
4. Update documentation

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings for all functions
- Write comprehensive tests

### Testing Guidelines

- Maintain test coverage above 90%
- Include unit, integration, and end-to-end tests
- Mock external dependencies
- Test error conditions and edge cases

## 🆘 Support

For support and questions:

1. Check the documentation in the `docs/` folder
2. Review the test examples
3. Open an issue on GitHub

## 🎯 Roadmap

- [ ] Enhanced personalization features
- [ ] Multi-language support
- [ ] Advanced workflow patterns
- [ ] Performance optimizations
- [ ] Additional tool integrations
- [ ] Real-time collaboration features

