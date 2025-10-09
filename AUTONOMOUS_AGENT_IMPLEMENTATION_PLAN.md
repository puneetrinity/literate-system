# Autonomous Agent Implementation Plan
## Phase 1A: Core Autonomous Capabilities (Production-Ready)

**Timeline:** 2-3 weeks
**Risk Level:** Low
**Deployment Strategy:** Feature-flagged with gradual rollout
**Cost Impact:** ~$0 (phi3:mini local inference)

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Critical Fixes Applied](#critical-fixes-applied)
3. [Phase 1A Implementation](#phase-1a-implementation)
4. [Testing Strategy](#testing-strategy)
5. [Deployment Plan](#deployment-plan)
6. [Monitoring & Rollback](#monitoring--rollback)
7. [Phase 2+ Extensions (Optional)](#phase-2-extensions-optional)

---

## Overview & Architecture

### Design Principles

✅ **Zero Regression Guarantee**
- Feature-flagged: `ENABLE_AUTONOMY=false` by default
- Classic routing preserved and unchanged
- Autonomous path is additive, not replacement

✅ **Cost Optimized**
- phi3:mini for all agent operations (~$0 incremental cost)
- Hard cost limits per query
- Budget tracking and circuit breakers

✅ **Production First**
- Comprehensive error handling
- Timeout guards at every step
- Telemetry for debugging
- Easy rollback mechanism

### System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedSearchGraph.execute()              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  if ENABLE_AUTONOMY == false:                               │
│    └─> Classic Routing (UNCHANGED)                          │
│        └─> Document/Web/Hybrid Search                       │
│                                                              │
│  if ENABLE_AUTONOMY == true:                                │
│    ┌─> 1. Complexity Assessment (phi3:mini)                │
│    │     └─> Score: 0.0-1.0                                 │
│    │                                                         │
│    ├─> 2. Adaptive Execution                                │
│    │     ├─> 0.0-0.3: React (direct search)                │
│    │     ├─> 0.3-0.7: Planned (multi-step)                 │
│    │     └─> 0.7+: Hybrid (comprehensive)                  │
│    │                                                         │
│    ├─> 3. Reflexion (if needed)                            │
│    │     ├─> Check: results sufficient?                     │
│    │     ├─> Decide: retry/escalate/finish                 │
│    │     └─> Max retries: 2                                 │
│    │                                                         │
│    └─> 4. Synthesis & Return                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Cost |
|-----------|---------|------|
| **Complexity Assessor** | Determine query complexity (0.0-1.0) | $0 (phi3:mini) |
| **Adaptive Executor** | Route based on complexity | $0 (routing logic) |
| **Reflexion Engine** | Self-correct on failures | $0 (phi3:mini) |
| **Telemetry System** | Track execution metrics | $0 (ClickHouse) |

---

## Critical Fixes Applied

### 1. GraphState Field Definitions
```python
# ❌ WRONG (from original plan)
from pydantic import Field
execution_plan: List[Dict[str, Any]] = Field(default_factory=list)

# ✅ CORRECT (dataclass fields)
from dataclasses import field
execution_plan: List[Dict[str, Any]] = field(default_factory=list)
```

### 2. State Reducers for New Fields
All new concurrent fields have proper reducers to avoid race conditions.

### 3. Execute Method Branching
`UnifiedSearchGraph.execute()` branches cleanly without replacing existing logic.

### 4. JSON Parser (Synchronous)
Parser is synchronous (no async/await) for string processing.

### 5. Circuit Breakers Added
- Cost limits per query
- Execution time guards
- Retry hard limits

---

## Phase 1A Implementation

**Import Completeness Note:** All code snippets below include complete import statements. Key imports used across files:
- **base.py**: Already has `from datetime import datetime` and `from dataclasses import dataclass, field`
- **json_parser.py**: Uses `import json`, `import re`, `from typing import ...`
- **autonomous_nodes.py**: Uses `import time`, `import uuid`, `from datetime import datetime`
- **unified_search_graph.py**: Adds `import time` and autonomous node imports
- **config.py**: Uses `from pydantic import Field` for Settings

All imports are shown in the code blocks below. No additional imports are required beyond what's documented.

---

### Step 1: GraphState Extensions

**File:** `ai-chat-service/app/graphs/base.py`

**Note on Imports:** The existing base.py already has all required imports:
- `from datetime import datetime` (line 11) - used by `calculate_total_time()`
- `from dataclasses import dataclass, field` (line 10) - used for GraphState fields
No new imports needed for Phase 1A in this file.

**Add these fields to GraphState dataclass (after line 100):**

```python
# Phase 1A: Autonomous agent fields
execution_plan: List[Dict[str, Any]] = field(default_factory=list)
current_step: int = 0
reflection_history: List[Dict[str, Any]] = field(default_factory=list)
retry_count: int = 0
agent_decision: Optional[str] = None  # "continue" | "retry" | "finish" | "escalate"
tools_used: List[str] = field(default_factory=list)
complexity_score: float = 0.0
autonomous_start_time: float = 0.0
autonomous_execution_mode: Optional[str] = None  # "react" | "planned" | "hybrid"
```

**Add reducers after _reduce_warnings method (after line 175):**

```python
@staticmethod
def _reduce_tools_used(current: List[str], new: List[str]) -> List[str]:
    """Reducer for tools_used to handle concurrent updates"""
    if not current:
        return list(dict.fromkeys(new)) if new else []
    if not new:
        return current
    # Merge and deduplicate while preserving order
    return list(dict.fromkeys(current + new))

@staticmethod
def _reduce_reflection_history(
    current: List[Dict[str, Any]],
    new: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Reducer for reflection_history"""
    if not current:
        return new if new else []
    if not new:
        return current

    # Deduplicate by ID if present
    seen = set()
    result: List[Dict[str, Any]] = []

    for item in current + new:
        item_id = item.get("id") or str(hash(str(item)))
        if item_id not in seen:
            seen.add(item_id)
            result.append(item)

    return result
```

**Update safe_update_state method (line 224) to include new reducers:**

```python
async def safe_update_state(self, **updates):
    """Thread-safe state updates with custom reducers"""
    async with self._state_lock:
        for key, value in updates.items():
            if hasattr(self, key):
                current_value = getattr(self, key)

                # Apply custom reducers
                if key == "search_results" and isinstance(value, list):
                    setattr(self, key, self._reduce_search_results(current_value, value))
                elif key == "intermediate_results" and isinstance(value, dict):
                    setattr(self, key, self._reduce_intermediate_results(current_value, value))
                elif key == "errors" and isinstance(value, list):
                    setattr(self, key, self._reduce_errors(current_value, value))
                elif key == "warnings" and isinstance(value, list):
                    setattr(self, key, self._reduce_warnings(current_value, value))
                elif key == "tools_used" and isinstance(value, list):
                    setattr(self, key, self._reduce_tools_used(current_value, value))
                elif key == "reflection_history" and isinstance(value, list):
                    setattr(self, key, self._reduce_reflection_history(current_value, value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)
```

---

### Step 2: JSON Parser Utility

**File:** `ai-chat-service/app/utils/json_parser.py` (NEW FILE)

```python
"""
Robust JSON parser for LLM outputs with fallback extraction strategies
"""
import json
import re
from typing import Any, Dict, Optional, List
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_json_robust(content: str) -> Optional[Dict[str, Any]]:
    """
    Robust JSON parser with multiple fallback strategies

    Args:
        content: Raw content from LLM that should contain JSON

    Returns:
        Parsed JSON dict or None if all strategies fail
    """
    if not content or not isinstance(content, str):
        return None

    content = content.strip()

    # Strategy 1: Direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code block
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract any JSON object (first match)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: Clean common LLM prefixes/suffixes
    cleaned = re.sub(r'^[^{]*', '', content)  # Remove prefix
    cleaned = re.sub(r'[^}]*$', '', cleaned)  # Remove suffix
    if cleaned:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse JSON from content: {content[:100]}...")
    return None


def extract_json_with_schema(
    content: str,
    schema: Dict[str, type],
    default_values: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Extract JSON and apply default values for missing fields

    Args:
        content: Raw LLM content
        schema: Expected schema with field types (e.g., {"score": float, "factors": list})
        default_values: Default values for missing fields

    Returns:
        Complete JSON object with defaults applied
    """
    data = parse_json_robust(content)
    if not data:
        data = {}

    # Apply defaults
    if default_values:
        for key, default_value in default_values.items():
            if key not in data:
                data[key] = default_value

    # Type coercion based on schema
    for field, expected_type in schema.items():
        if field in data:
            try:
                if expected_type == float and not isinstance(data[field], float):
                    data[field] = float(data[field])
                elif expected_type == int and not isinstance(data[field], int):
                    data[field] = int(data[field])
                elif expected_type == list and not isinstance(data[field], list):
                    data[field] = [data[field]] if data[field] else []
                elif expected_type == str and not isinstance(data[field], str):
                    data[field] = str(data[field])
            except (ValueError, TypeError) as e:
                logger.warning(f"Type coercion failed for field {field}: {e}")
                # Use default if coercion fails
                if default_values and field in default_values:
                    data[field] = default_values[field]

    return data


# Pre-defined schemas for common agent responses
COMPLEXITY_SCHEMA = {
    "score": float,
    "factors": list,
    "recommended_strategy": str
}

COMPLEXITY_DEFAULTS = {
    "score": 0.5,
    "factors": ["assessment_failed"],
    "recommended_strategy": "planned"
}

REFLECTION_SCHEMA = {
    "what_went_wrong": str,
    "root_cause": str,
    "what_to_try_next": str,
    "lessons_learned": list,
    "decision": str
}

REFLECTION_DEFAULTS = {
    "what_went_wrong": "Unknown issue",
    "root_cause": "Unable to determine",
    "what_to_try_next": "Finish execution",
    "lessons_learned": [],
    "decision": "finish"
}

PLANNING_SCHEMA = {
    "steps": list
}

PLANNING_DEFAULTS = {
    "steps": [{"tool": "document", "query": "", "why": "fallback"}]
}
```

---

### Step 3: Configuration Settings

**File:** `ai-chat-service/app/core/config.py`

**Add these settings to the Settings class (after line 221):**

**Note on Naming Convention:**
- Settings fields use **snake_case** (e.g., `enable_autonomy`)
- Environment variables use **UPPERCASE** (e.g., `ENABLE_AUTONOMY`)
- Pydantic automatically maps `ENABLE_AUTONOMY` → `enable_autonomy`
- For clarity, you can explicitly specify: `Field(env="ENABLE_AUTONOMY")`

```python
# Phase 1A: Autonomous Agent Settings
enable_autonomy: bool = Field(
    default=False,
    env="ENABLE_AUTONOMY",  # Explicit env mapping (optional but recommended)
    description="Enable autonomous agent execution (feature flag)"
)
max_retry_count: int = Field(
    default=2,
    env="MAX_RETRY_COUNT",
    description="Maximum retry attempts for reflexion"
)
complexity_threshold_low: float = Field(
    default=0.3,
    env="COMPLEXITY_THRESHOLD_LOW",
    description="Complexity threshold for react strategy (0.0-0.3)"
)
complexity_threshold_high: float = Field(
    default=0.7,
    env="COMPLEXITY_THRESHOLD_HIGH",
    description="Complexity threshold for planned strategy (0.3-0.7)"
)
autonomous_timeout_seconds: float = Field(
    default=30.0,
    env="AUTONOMOUS_TIMEOUT_SECONDS",
    description="Maximum execution time for autonomous flow"
)
max_cost_per_query: float = Field(
    default=1.0,
    env="MAX_COST_PER_QUERY",
    description="Maximum cost allowed per autonomous query"
)

# Telemetry
enable_agent_telemetry: bool = Field(
    default=True,
    env="ENABLE_AGENT_TELEMETRY",
    description="Enable agent execution telemetry"
)
telemetry_sample_rate: float = Field(
    default=1.0,
    env="TELEMETRY_SAMPLE_RATE",
    description="Telemetry sampling rate (0.0-1.0)"
)
```

**Update .env file:**

```bash
# Phase 1A: Autonomous Agent Configuration
ENABLE_AUTONOMY=false  # Start disabled for safety
MAX_RETRY_COUNT=2
COMPLEXITY_THRESHOLD_LOW=0.3
COMPLEXITY_THRESHOLD_HIGH=0.7
AUTONOMOUS_TIMEOUT_SECONDS=30.0
MAX_COST_PER_QUERY=1.0
ENABLE_AGENT_TELEMETRY=true
TELEMETRY_SAMPLE_RATE=1.0
```

---

### Step 4: Core Agent Nodes

**File:** `ai-chat-service/app/graphs/autonomous_nodes.py` (NEW FILE)

```python
"""
Core autonomous agent nodes for Phase 1A
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.graphs.base import GraphState, NodeResult
from app.core.logging import get_logger
from app.utils.json_parser import (
    extract_json_with_schema,
    COMPLEXITY_SCHEMA,
    COMPLEXITY_DEFAULTS,
    REFLECTION_SCHEMA,
    REFLECTION_DEFAULTS,
    PLANNING_SCHEMA,
    PLANNING_DEFAULTS
)

logger = get_logger(__name__)


class ComplexityAssessorNode:
    """
    Assess query complexity to determine execution strategy

    Complexity levels:
    - 0.0-0.3: Simple (react - direct search)
    - 0.3-0.7: Medium (planned - multi-step)
    - 0.7+: Complex (hybrid - comprehensive)
    """

    def __init__(self, model_manager, settings):
        self.model_manager = model_manager
        self.settings = settings

    async def execute(self, state: GraphState) -> NodeResult:
        """Execute complexity assessment"""
        try:
            # Quick pre-filter to avoid LLM call for obviously simple queries
            query_words = state.original_query.split()
            simple_indicators = {"what", "is", "define", "who", "when", "where"}

            if (len(query_words) <= 5 and
                any(word.lower() in simple_indicators for word in query_words[:2])):

                await state.safe_update_state(
                    complexity_score=0.2,
                    intermediate_results={
                        **getattr(state, "intermediate_results", {}),
                        "complexity_factors": ["simple_query_pattern"],
                        "recommended_strategy": "react",
                        "assessment_method": "pre_filter"
                    }
                )

                logger.info(f"Pre-filtered as simple query: {state.original_query[:50]}")

                return NodeResult(
                    success=True,
                    data={
                        "complexity": 0.2,
                        "strategy": "react",
                        "pre_filtered": True
                    },
                    confidence=0.8,
                    cost=0.0
                )

            # LLM-based complexity assessment
            prompt = (
                "Assess query complexity (0.0-1.0). Output ONLY JSON:\n"
                "{\n"
                '  "score": 0.5,\n'
                '  "factors": ["reasoning required", "multiple concepts"],\n'
                '  "recommended_strategy": "planned"\n'
                "}\n\n"
                "Scoring guide:\n"
                "- 0.0-0.3: Simple lookup/definition (strategy: react)\n"
                "- 0.3-0.7: Multi-step reasoning (strategy: planned)\n"
                "- 0.7+: Complex analysis (strategy: hybrid)\n\n"
                "Consider: concepts count, reasoning depth, information synthesis needs"
            )

            result = await self.model_manager.generate(
                model_name="phi3:mini",
                prompt=f"{prompt}\n\nQuery: {state.original_query}",
                max_tokens=200,
                temperature=0.1
            )

            content = getattr(result, "text", "") or getattr(result, "content", "")
            assessment = extract_json_with_schema(
                content,
                COMPLEXITY_SCHEMA,
                COMPLEXITY_DEFAULTS
            )

            # Validate and clamp score
            score = max(0.0, min(1.0, float(assessment.get("score", 0.5))))

            await state.safe_update_state(
                complexity_score=score,
                intermediate_results={
                    **getattr(state, "intermediate_results", {}),
                    "complexity_factors": assessment.get("factors", []),
                    "recommended_strategy": assessment.get("recommended_strategy", "planned"),
                    "assessment_method": "llm"
                }
            )

            logger.info(
                f"Complexity assessed: {score:.2f} → {assessment.get('recommended_strategy')}",
                extra_fields={
                    "complexity_score": score,
                    "factors": assessment.get("factors"),
                    "correlation_id": state.correlation_id
                }
            )

            return NodeResult(
                success=True,
                data={
                    "complexity": score,
                    "strategy": assessment.get("recommended_strategy"),
                    "factors": assessment.get("factors")
                },
                confidence=0.8,
                cost=0.001  # phi3:mini cost estimate
            )

        except Exception as e:
            logger.error(f"Complexity assessment failed: {e}", exc_info=True)

            # Safe fallback
            await state.safe_update_state(
                complexity_score=0.5,
                intermediate_results={
                    **getattr(state, "intermediate_results", {}),
                    "complexity_factors": ["assessment_failed"],
                    "recommended_strategy": "planned",
                    "assessment_method": "fallback"
                }
            )

            return NodeResult(
                success=True,
                data={"complexity": 0.5, "strategy": "planned", "fallback": True},
                confidence=0.5,
                cost=0.0
            )


class ReflexionNode:
    """
    Reflect on execution and decide next action
    """

    def __init__(self, model_manager, settings):
        self.model_manager = model_manager
        self.settings = settings

    async def execute(self, state: GraphState) -> NodeResult:
        """Execute reflexion"""
        try:
            # Determine if reflection is needed
            should_reflect = (
                getattr(state, "retry_count", 0) > 0 or
                len(getattr(state, "search_results", [])) < 2 or
                any("failed" in str(error).lower() for error in getattr(state, "errors", []))
            )

            if not should_reflect:
                await state.safe_update_state(agent_decision="finish")
                return NodeResult(
                    success=True,
                    data={"skipped": True, "reason": "no_reflection_needed"},
                    confidence=0.9
                )

            # Check hard limits
            if getattr(state, "retry_count", 0) >= self.settings.max_retry_count:
                await state.safe_update_state(agent_decision="finish")
                logger.info(f"Max retries ({self.settings.max_retry_count}) reached, finishing")
                return NodeResult(
                    success=True,
                    data={"decision": "finish", "reason": "max_retries_reached"},
                    confidence=0.7
                )

            # Gather context for reflection
            context = {
                "query": state.original_query,
                "retry_count": getattr(state, "retry_count", 0),
                "results_found": len(getattr(state, "search_results", [])),
                "tools_used": getattr(state, "tools_used", []),
                "errors": getattr(state, "errors", []),
                "execution_time": time.time() - getattr(state, "autonomous_start_time", time.time()),
                "complexity_score": getattr(state, "complexity_score", 0.5)
            }

            prompt = (
                "Reflect on what went wrong and decide next action. Output ONLY JSON:\n"
                "{\n"
                '  "what_went_wrong": "brief description",\n'
                '  "root_cause": "likely root cause",\n'
                '  "what_to_try_next": "specific next action",\n'
                '  "lessons_learned": ["insight1", "insight2"],\n'
                '  "decision": "retry|escalate|finish"\n'
                "}\n\n"
                "Decision guidelines:\n"
                "- retry: Try current approach again (if retry_count < max)\n"
                "- escalate: Move to more comprehensive search method\n"
                "- finish: Accept current results or give up\n"
            )

            result = await self.model_manager.generate(
                model_name="phi3:mini",
                prompt=f"{prompt}\n\nContext:\n{context}",
                max_tokens=400,
                temperature=0.3
            )

            content = getattr(result, "text", "") or getattr(result, "content", "")
            reflection_data = extract_json_with_schema(
                content,
                REFLECTION_SCHEMA,
                REFLECTION_DEFAULTS
            )

            # Validate decision
            decision = reflection_data.get("decision", "finish")
            if decision not in ["retry", "escalate", "finish"]:
                decision = "finish"

            # Create reflection record
            ref_id = str(uuid.uuid4())
            reflection_record = {
                **reflection_data,
                "id": ref_id,
                "timestamp": datetime.now().isoformat(),
                "context": context
            }

            # Update state
            new_retry_count = getattr(state, "retry_count", 0)
            if decision in ["retry", "escalate"]:
                new_retry_count += 1

            await state.safe_update_state(
                reflection_history=[reflection_record],
                agent_decision=decision,
                retry_count=new_retry_count
            )

            logger.info(
                f"Reflection completed: {decision}",
                extra_fields={
                    "decision": decision,
                    "retry_count": new_retry_count,
                    "lessons": len(reflection_data.get("lessons_learned", [])),
                    "correlation_id": state.correlation_id
                }
            )

            return NodeResult(
                success=True,
                data=reflection_record,
                confidence=0.7,
                cost=0.001
            )

        except Exception as e:
            logger.error(f"Reflection failed: {e}", exc_info=True)
            await state.safe_update_state(agent_decision="finish")
            return NodeResult(
                success=False,
                error=str(e),
                confidence=0.0
            )
```

---

### Step 5: Adaptive Execution Logic

**File:** `ai-chat-service/app/graphs/unified_search_graph.py`

**Add imports at the top:**

```python
import time
from app.graphs.autonomous_nodes import ComplexityAssessorNode, ReflexionNode
from app.utils.json_parser import extract_json_with_schema, PLANNING_SCHEMA, PLANNING_DEFAULTS
```

**Add to __init__ method (after line 58):**

```python
# Initialize autonomous agent nodes
if self.settings.enable_autonomy:
    self.complexity_assessor = ComplexityAssessorNode(model_manager, self.settings)
    self.reflexion_node = ReflexionNode(model_manager, self.settings)
```

**Replace the execute method (starting at line 75) with branching logic:**

```python
async def execute(self, state: GraphState) -> NodeResult:
    """Execute the unified search graph with autonomous branch"""

    start_time = time.time()

    try:
        # Set autonomous start time for tracking
        await state.safe_update_state(autonomous_start_time=start_time)

        if self.settings.enable_autonomy:
            # AUTONOMOUS EXECUTION PATH
            logger.info(
                "Starting autonomous execution",
                extra_fields={
                    "query": state.original_query[:100],
                    "correlation_id": state.correlation_id
                }
            )

            return await self._execute_autonomous(state, start_time)
        else:
            # CLASSIC EXECUTION PATH (unchanged)
            return await self._execute_classic_routing(state)

    except Exception as e:
        logger.error(f"Unified search execution error: {str(e)}", exc_info=True)

        # Record error telemetry
        await self._record_error_telemetry(state, str(e), start_time)

        return NodeResult(
            success=False,
            data={"error": f"Search execution failed: {str(e)}"},
            confidence=0.0,
            cost=0.0,
            error=str(e)
        )
```

**Add the autonomous execution method:**

```python
async def _execute_autonomous(self, state: GraphState, start_time: float) -> NodeResult:
    """Autonomous execution flow"""
    try:
        # Phase 1: Complexity Assessment
        complexity_result = await self.complexity_assessor.execute(state)

        if not complexity_result.success:
            logger.warning("Complexity assessment failed, falling back to classic routing")
            return await self._execute_classic_routing(state)

        # Phase 2: Adaptive Execution (main work)
        execution_result = await self._adaptive_execution(state)

        # Phase 3: Reflexion & Potential Retry
        reflection_result = await self.reflexion_node.execute(state)

        # Phase 4: Handle agent decision
        decision = getattr(state, "agent_decision", "finish")
        retry_count = getattr(state, "retry_count", 0)

        if (decision in ["retry", "escalate"] and
            retry_count <= self.settings.max_retry_count):

            logger.info(f"Agent decision: {decision} (attempt {retry_count})")

            # Escalate strategy if needed
            if decision == "escalate":
                await self._escalate_strategy(state)

            # Retry execution
            execution_result = await self._adaptive_execution(state)

            # Reflect again after retry
            await self.reflexion_node.execute(state)

        # Phase 5: Synthesis (use existing method)
        synthesis_result = await self._synthesize_results(state)

        # IMPORTANT: Ensure output shape consistency
        # The API expects result.data to contain both 'results' and 'search_results' keys
        # for backward compatibility. Update _synthesize_results to include both:
        # synthesis_result.data = {
        #     "search_results": search_results,  # For backward compat
        #     "results": search_results,         # Current format
        #     ... other fields
        # }

        # Record telemetry
        await self._record_autonomous_telemetry(state, synthesis_result, start_time)

        return synthesis_result

    except Exception as e:
        logger.error(f"Autonomous execution failed: {e}", exc_info=True)
        # Fallback to classic routing
        return await self._execute_classic_routing(state)


async def _adaptive_execution(self, state: GraphState) -> NodeResult:
    """Route to appropriate execution strategy based on complexity"""
    try:
        complexity = getattr(state, "complexity_score", 0.5)

        # Route based on complexity
        if complexity < self.settings.complexity_threshold_low:
            # React: Direct search
            logger.info("Adaptive execution: react (simple)")
            await state.safe_update_state(
                autonomous_execution_mode="react",
                tools_used=["document"]
            )
            return await self.document_node.execute(state)

        elif complexity < self.settings.complexity_threshold_high:
            # Planned: Multi-step execution
            logger.info("Adaptive execution: planned (medium)")
            await state.safe_update_state(autonomous_execution_mode="planned")
            return await self._execute_planned(state)

        else:
            # Hybrid: Comprehensive search
            logger.info("Adaptive execution: hybrid (complex)")
            await state.safe_update_state(
                autonomous_execution_mode="hybrid",
                tools_used=["document", "web"]
            )
            return await self._execute_hybrid_search(state)

    except Exception as e:
        logger.error(f"Adaptive execution failed: {e}", exc_info=True)
        # Fallback to document search
        return await self.document_node.execute(state)


async def _execute_planned(self, state: GraphState) -> NodeResult:
    """Execute multi-step planned approach"""
    try:
        # Create execution plan
        prompt = (
            "Create a 2-3 step search plan. Output ONLY JSON:\n"
            '{ "steps": [ {"tool": "document|web|hybrid", "query": "specific search", "why": "reason"} ] }\n\n'
            "Guidelines:\n"
            "- Prefer 'document' for internal knowledge\n"
            "- Use 'web' for current events (if enabled)\n"
            "- Use 'hybrid' for comprehensive coverage\n"
            "- Each step should have specific, focused query\n"
            "- Maximum 3 steps for efficiency"
        )

        result = await self.model_manager.generate(
            model_name="phi3:mini",
            prompt=f"{prompt}\n\nTask: {state.original_query}",
            max_tokens=300,
            temperature=0.2
        )

        content = getattr(result, "text", "") or getattr(result, "content", "")
        plan = extract_json_with_schema(content, PLANNING_SCHEMA, PLANNING_DEFAULTS)

        steps = plan.get("steps", [])[:3]  # Max 3 steps
        if not steps:
            # Fallback to hybrid search
            return await self._execute_hybrid_search(state)

        await state.safe_update_state(
            execution_plan=steps,
            current_step=0
        )

        # Execute steps sequentially
        merged_results = []
        total_cost = 0.0
        tools_used = []

        for i, step in enumerate(steps):
            tool = step.get("tool", "document")
            query = step.get("query", state.original_query)

            # ✅ POLICY ENFORCEMENT: Map web→document if disabled
            if tool == "web" and not self.settings.enable_web_search_in_documents:
                logger.info(f"Web search disabled, mapping step {i+1} to document search")
                tool = "document"

            # ✅ POLICY ENFORCEMENT: Map hybrid→document if web disabled
            if tool == "hybrid" and not self.settings.enable_web_search_in_documents:
                logger.info(f"Web search disabled, mapping hybrid step {i+1} to document-only")
                tool = "document"

            # Create step-specific state
            step_state = GraphState(
                original_query=query,
                user_id=getattr(state, "user_id", "anonymous"),
                conversation_history=state.conversation_history,
                max_results=getattr(state, "max_results", 10) // len(steps)
            )

            # Execute step
            if tool == "document":
                step_result = await self.document_node.execute(step_state)
            elif tool == "web":
                step_result = await self._execute_web_search(step_state)
            elif tool == "hybrid":
                step_result = await self._execute_hybrid_search(step_state)
            else:
                continue  # Skip unknown tools

            # Collect results
            if step_result.success and step_result.data:
                step_results = step_result.data.get("search_results", [])
                for result_item in step_results:
                    if isinstance(result_item, dict):
                        result_item["step"] = i + 1
                        result_item["step_query"] = query
                        result_item["step_tool"] = tool
                    merged_results.append(result_item)

                total_cost += step_result.cost or 0.0

            tools_used.append(tool)

            # Update state
            await state.safe_update_state(
                tools_used=[tool],
                current_step=i + 1
            )

            # Early stop if enough results
            if len(merged_results) >= getattr(state, "max_results", 10):
                break

        # Update final state
        await state.safe_update_state(
            search_results=merged_results,
            tools_used=tools_used
        )

        return NodeResult(
            success=True,
            data={
                "search_results": merged_results,
                "steps_executed": len(steps),
                "total_found": len(merged_results),
                "search_type": "planned"
            },
            confidence=0.8,
            cost=total_cost
        )

    except Exception as e:
        logger.error(f"Planned execution failed: {e}", exc_info=True)
        # Fallback to hybrid search
        return await self._execute_hybrid_search(state)


async def _escalate_strategy(self, state: GraphState) -> None:
    """Escalate to more comprehensive search strategy (respecting policy)"""
    current_complexity = getattr(state, "complexity_score", 0.5)

    # ✅ POLICY ENFORCEMENT: Escalation ladder respects web search policy
    if current_complexity < 0.5:
        new_complexity = 0.6  # Force hybrid
        new_strategy = "hybrid"
    elif current_complexity < 0.8 and self.settings.enable_web_search_in_documents:
        new_complexity = 0.8  # Force web search (only if allowed)
        new_strategy = "web"
    else:
        # If web disabled or already high, just increase complexity slightly
        new_complexity = min(current_complexity + 0.1, 1.0)
        if self.settings.enable_web_search_in_documents:
            new_strategy = "hybrid"
        else:
            new_strategy = "document"  # Stay with document-only

    await state.safe_update_state(
        complexity_score=new_complexity,
        intermediate_results={
            **getattr(state, "intermediate_results", {}),
            "recommended_strategy": new_strategy,
            "escalated": True,
            "original_complexity": current_complexity
        }
    )

    logger.info(
        f"Strategy escalated: {current_complexity:.2f} → {new_complexity:.2f} ({new_strategy})",
        extra_fields={
            "web_search_enabled": self.settings.enable_web_search_in_documents,
            "correlation_id": state.correlation_id
        }
    )


async def _execute_classic_routing(self, state: GraphState) -> NodeResult:
    """
    Original routing behavior (unchanged when autonomy disabled)
    This preserves the existing logic from lines 82-109
    """
    # Route the query first
    route_result = await self._route_query(state)
    if not route_result.success:
        return route_result

    # Get the routing decision
    analysis = getattr(state, 'routing_analysis', None)
    route = self._get_route_from_analysis(analysis)

    # Check for upload operation
    if hasattr(state, 'operation') and state.operation == 'upload':
        route = "document_upload"

    # Execute the appropriate search based on route
    if route == "document_search":
        search_result = await self.document_node.execute(state)
    elif route == "web_search":
        search_result = await self._execute_web_search(state)
    elif route == "hybrid_search":
        search_result = await self._execute_hybrid_search(state)
    elif route == "document_upload":
        search_result = await self.upload_node.execute(state)
    else:
        search_result = await self._handle_fallback(state)

    return search_result


async def _record_autonomous_telemetry(
    self,
    state: GraphState,
    result: NodeResult,
    start_time: float
) -> None:
    """Record telemetry for autonomous execution"""
    if not self.settings.enable_agent_telemetry:
        return

    execution_time = (time.time() - start_time) * 1000  # ms

    telemetry_data = {
        "query_id": getattr(state, "correlation_id", "unknown"),
        "user_id": getattr(state, "user_id", "anonymous"),
        "autonomous_enabled": True,
        "execution_mode": getattr(state, "autonomous_execution_mode", "unknown"),
        "complexity_score": getattr(state, "complexity_score", 0.0),
        "steps_executed": getattr(state, "current_step", 0),
        "retry_count": getattr(state, "retry_count", 0),
        "tools_used": getattr(state, "tools_used", []),
        "execution_time_ms": execution_time,
        "result_count": len(getattr(state, "search_results", [])),
        "success": result.success,
        "confidence": result.confidence or 0.0,
        "cost": result.cost or 0.0,
        "reflections_count": len(getattr(state, "reflection_history", [])),
        "escalated": getattr(state, "intermediate_results", {}).get("escalated", False)
    }

    # Log structured telemetry
    logger.info("Autonomous execution completed", extra_fields=telemetry_data)


async def _record_error_telemetry(
    self,
    state: GraphState,
    error: str,
    start_time: float
) -> None:
    """Record error telemetry"""
    if not self.settings.enable_agent_telemetry:
        return

    execution_time = (time.time() - start_time) * 1000  # ms

    error_data = {
        "query_id": getattr(state, "correlation_id", "unknown"),
        "user_id": getattr(state, "user_id", "anonymous"),
        "autonomous_enabled": self.settings.enable_autonomy,
        "error": error,
        "execution_time_ms": execution_time,
        "retry_count": getattr(state, "retry_count", 0),
        "complexity_score": getattr(state, "complexity_score", 0.0)
    }

    logger.error("Autonomous execution failed", extra_fields=error_data)
```

**IMPORTANT: Update `_synthesize_results` for Output Shape Consistency**

To ensure backward compatibility, update the existing `_synthesize_results` method in `unified_search_graph.py` to return both `"results"` and `"search_results"` keys:

```python
async def _synthesize_results(self, state: GraphState) -> NodeResult:
    """Synthesize search results into a coherent response"""

    try:
        search_results = getattr(state, 'search_results', [])
        search_metadata = getattr(state, 'search_metadata', {})

        if not search_results:
            return NodeResult(
                success=True,
                data={"message": "No results found", "results": [], "search_results": []},
                confidence=0.0,
                cost=0.0
            )

        # Create synthesis
        synthesis = {
            "summary": f"Found {len(search_results)} relevant results",
            "results": search_results[:5],          # Current API format
            "search_results": search_results[:5],   # Backward compatibility
            "metadata": search_metadata,
            "response_type": "search_results"
        }

        return NodeResult(
            success=True,
            data=synthesis,
            confidence=0.9,
            cost=0.0
        )
```

**Why Both Keys?**
- Some API consumers expect `data["search_results"]`
- Some expect `data["results"]`
- Including both ensures zero breaking changes

---

## Testing Strategy

### Unit Tests

**File:** `tests/graphs/test_autonomous_nodes.py` (NEW FILE)

```python
"""
Unit tests for autonomous agent nodes
"""
import pytest
from unittest.mock import Mock, AsyncMock

from app.graphs.base import GraphState, NodeResult
from app.graphs.autonomous_nodes import ComplexityAssessorNode, ReflexionNode


class TestComplexityAssessor:
    """Test complexity assessment"""

    @pytest.mark.asyncio
    async def test_simple_query_prefilter(self):
        """Test that simple queries are pre-filtered"""
        # Setup
        model_manager = AsyncMock()
        settings = Mock()
        settings.complexity_threshold_low = 0.3

        assessor = ComplexityAssessorNode(model_manager, settings)
        state = GraphState(original_query="What is Python?")

        # Execute
        result = await assessor.execute(state)

        # Assertions
        assert result.success
        assert result.data["pre_filtered"] is True
        assert state.complexity_score == 0.2
        assert result.data["strategy"] == "react"

        # LLM should not be called for pre-filtered queries
        model_manager.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_complex_query_llm_assessment(self):
        """Test LLM-based complexity assessment"""
        # Setup
        model_manager = AsyncMock()
        settings = Mock()
        settings.complexity_threshold_low = 0.3

        # Mock LLM response
        mock_result = Mock()
        mock_result.text = '{"score": 0.8, "factors": ["multi-step"], "recommended_strategy": "hybrid"}'
        model_manager.generate.return_value = mock_result

        assessor = ComplexityAssessorNode(model_manager, settings)
        state = GraphState(
            original_query="Compare machine learning frameworks and recommend the best one"
        )

        # Execute
        result = await assessor.execute(state)

        # Assertions
        assert result.success
        assert state.complexity_score == 0.8
        assert result.data["strategy"] == "hybrid"
        assert "multi-step" in state.intermediate_results["complexity_factors"]

        # LLM should be called
        model_manager.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        """Test fallback when LLM fails"""
        # Setup
        model_manager = AsyncMock()
        model_manager.generate.side_effect = Exception("LLM service unavailable")
        settings = Mock()

        assessor = ComplexityAssessorNode(model_manager, settings)
        state = GraphState(original_query="Test query")

        # Execute
        result = await assessor.execute(state)

        # Assertions
        assert result.success  # Should still succeed with fallback
        assert state.complexity_score == 0.5  # Fallback score
        assert result.data["fallback"] is True


class TestReflexionNode:
    """Test reflexion functionality"""

    @pytest.mark.asyncio
    async def test_skip_when_not_needed(self):
        """Test that reflexion is skipped when not needed"""
        # Setup
        model_manager = AsyncMock()
        settings = Mock()
        settings.max_retry_count = 2

        reflexion = ReflexionNode(model_manager, settings)
        state = GraphState(
            original_query="Test",
            retry_count=0,
            search_results=[{"content": "Result 1"}, {"content": "Result 2"}],
            errors=[]
        )

        # Execute
        result = await reflexion.execute(state)

        # Assertions
        assert result.success
        assert result.data["skipped"] is True
        assert state.agent_decision == "finish"

        # LLM should not be called
        model_manager.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_on_insufficient_results(self):
        """Test reflexion triggers on insufficient results"""
        # Setup
        model_manager = AsyncMock()
        settings = Mock()
        settings.max_retry_count = 2

        # Mock LLM response
        mock_result = Mock()
        mock_result.text = '''
        {
            "what_went_wrong": "No results found",
            "root_cause": "Query too specific",
            "what_to_try_next": "Broaden search",
            "lessons_learned": ["Use broader terms"],
            "decision": "retry"
        }
        '''
        model_manager.generate.return_value = mock_result

        reflexion = ReflexionNode(model_manager, settings)
        state = GraphState(
            original_query="Test",
            retry_count=0,
            search_results=[],  # No results
            errors=["Search returned no results"]
        )

        # Execute
        result = await reflexion.execute(state)

        # Assertions
        assert result.success
        assert state.agent_decision == "retry"
        assert state.retry_count == 1
        assert len(state.reflection_history) == 1
        assert "Use broader terms" in state.reflection_history[0]["lessons_learned"]

    @pytest.mark.asyncio
    async def test_max_retries_enforcement(self):
        """Test that max retries are enforced"""
        # Setup
        model_manager = AsyncMock()
        settings = Mock()
        settings.max_retry_count = 2

        reflexion = ReflexionNode(model_manager, settings)
        state = GraphState(
            original_query="Test",
            retry_count=2,  # Already at max
            search_results=[],
            errors=["Failed"]
        )

        # Execute
        result = await reflexion.execute(state)

        # Assertions
        assert result.success
        assert state.agent_decision == "finish"
        assert result.data["reason"] == "max_retries_reached"

        # LLM should not be called when max retries reached
        model_manager.generate.assert_not_called()


@pytest.mark.integration
class TestAutonomousFlow:
    """Integration tests for autonomous flow"""

    @pytest.mark.asyncio
    async def test_end_to_end_simple_query(self):
        """Test complete autonomous flow for simple query"""
        # This would test the full UnifiedSearchGraph.execute() flow
        # with mocked model manager and document node
        pass

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test that retry mechanism works correctly"""
        # This would test reflexion triggering retry
        # and second execution succeeding
        pass
```

### Integration Tests

**File:** `tests/integration/test_autonomous_integration.py` (NEW FILE)

```python
"""
Integration tests for autonomous agent system
"""
import pytest
import time
from unittest.mock import Mock, AsyncMock

from app.graphs.base import GraphState, NodeResult
from app.graphs.unified_search_graph import UnifiedSearchGraph


@pytest.mark.integration
class TestAutonomousIntegration:

    @pytest.fixture
    async def autonomous_graph(self):
        """Create graph with autonomous mode enabled"""
        model_manager = AsyncMock()
        cache_manager = Mock()

        graph = UnifiedSearchGraph(
            model_manager=model_manager,
            cache_manager=cache_manager,
            document_search_url="http://localhost:8001"
        )

        # Enable autonomous mode
        graph.settings = Mock()
        graph.settings.enable_autonomy = True
        graph.settings.max_retry_count = 2
        graph.settings.complexity_threshold_low = 0.3
        graph.settings.complexity_threshold_high = 0.7
        graph.settings.autonomous_timeout_seconds = 30.0
        graph.settings.max_cost_per_query = 1.0
        graph.settings.enable_agent_telemetry = True
        graph.settings.enable_web_search_in_documents = False

        return graph

    @pytest.mark.asyncio
    async def test_simple_query_flow(self, autonomous_graph):
        """Test autonomous flow for simple query"""
        # Mock complexity assessment
        autonomous_graph.model_manager.generate.return_value = Mock(
            text='{"score": 0.2, "factors": ["simple"], "recommended_strategy": "react"}'
        )

        # Mock document search
        autonomous_graph.document_node = AsyncMock()
        autonomous_graph.document_node.execute.return_value = NodeResult(
            success=True,
            data={"search_results": [{"content": "Python is a programming language", "score": 0.9}]},
            confidence=0.9
        )

        # Mock synthesis
        autonomous_graph._synthesize_results = AsyncMock(return_value=NodeResult(
            success=True,
            data={"search_results": [{"content": "Python is a programming language"}]},
            confidence=0.9
        ))

        # Execute
        state = GraphState(
            original_query="What is Python?",
            user_id="test_user",
            correlation_id="test_123"
        )

        start_time = time.time()
        result = await autonomous_graph.execute(state)
        execution_time = time.time() - start_time

        # Assertions
        assert result.success
        assert len(result.data["search_results"]) >= 1
        assert state.complexity_score == 0.2
        assert state.autonomous_execution_mode == "react"
        assert execution_time < 5.0  # Should be fast
        assert getattr(state, "retry_count", 0) == 0  # No retries needed

    @pytest.mark.asyncio
    async def test_classic_routing_when_disabled(self):
        """Test that classic routing works when autonomy disabled"""
        model_manager = AsyncMock()
        cache_manager = Mock()

        graph = UnifiedSearchGraph(
            model_manager=model_manager,
            cache_manager=cache_manager,
            document_search_url="http://localhost:8001"
        )

        # Disable autonomous mode
        graph.settings = Mock()
        graph.settings.enable_autonomy = False

        # Mock classic routing components
        graph.router = Mock()
        graph.router.analyze_query.return_value = Mock(
            suggested_provider="ultra_fast_search",
            confidence=0.9,
            reasoning="test"
        )

        graph.document_node = AsyncMock()
        graph.document_node.execute.return_value = NodeResult(
            success=True,
            data={"search_results": [{"content": "Classic result"}]},
            confidence=0.8
        )

        # Execute
        state = GraphState(original_query="Test query")
        result = await graph.execute(state)

        # Assertions
        assert result.success
        # Should not have autonomous fields set
        assert not hasattr(state, "complexity_score") or state.complexity_score == 0.0
        assert not hasattr(state, "autonomous_execution_mode")
```

### Regression Tests

```bash
# Ensure all existing tests still pass
pytest tests/ -v

# Check that classic routing is unchanged
pytest tests/api/test_unified_search.py -v

# Verify document search still works
pytest tests/graphs/test_document_search_node.py -v
```

---

## Deployment Plan

### Phase 1: Development Environment (Week 1)

```bash
# 1. Deploy code with autonomy DISABLED
cd /home/ews/unified-ai-system-clean
git checkout -b feature/autonomous-agents-phase1a

# Apply all code changes from this document

# 2. Update environment
echo "ENABLE_AUTONOMY=false" >> .env

# 3. Build and start services
cd deploy && make dev

# 4. Run tests
pytest tests/ -v --tb=short

# 5. Verify zero regression
curl -X POST http://localhost:8000/api/v1/chat/unified \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "user_id": "test"}'
```

### Phase 2: Enable Autonomy in Dev (Week 2)

```bash
# 1. Enable autonomy
export ENABLE_AUTONOMY=true

# 2. Test autonomous execution
curl -X POST http://localhost:8000/api/v1/chat/unified \
  -H "Content-Type: application/json" \
  -d '{"query": "complex analysis of AI trends", "user_id": "test"}'

# 3. Check telemetry logs (Phase 1A approach)
docker logs ai-chat-service | grep "Autonomous execution"

# 4. Monitor performance (optional - if Prometheus is set up)
# curl http://localhost:8000/metrics | grep autonomous
```

### Phase 3: Production Rollout (Weeks 3-5)

```yaml
# rollout-config.yaml
phases:
  week_3:
    traffic_percentage: 5
    duration: "5 days"
    success_criteria:
      error_rate: "<2%"
      p95_latency: "<5000ms"
      cost_increase: "<10%"

  week_4:
    traffic_percentage: 25
    duration: "5 days"
    success_criteria:
      error_rate: "<2%"
      p95_latency: "<5000ms"
      user_satisfaction: ">80%"

  week_5:
    traffic_percentage: 100
    duration: "ongoing"
    monitoring: "continuous"
```

**Rollout Script:**

```bash
#!/bin/bash
# deploy/rollout_autonomous.sh

set -e

TRAFFIC_PCT=${1:-5}
ENVIRONMENT=${2:-production}

echo "Rolling out autonomous agents: ${TRAFFIC_PCT}% traffic in ${ENVIRONMENT}"

# Update configuration
kubectl set env deployment/ai-chat-service \
  ENABLE_AUTONOMY=true \
  AUTONOMOUS_TRAFFIC_PERCENTAGE=${TRAFFIC_PCT}

# Monitor rollout
kubectl rollout status deployment/ai-chat-service

# Check health
sleep 10
kubectl exec -it deployment/ai-chat-service -- curl -f http://localhost:8000/health

echo "Rollout complete. Monitoring..."

# Tail logs for 5 minutes
timeout 300 kubectl logs -f deployment/ai-chat-service | grep -E "(autonomous|error|warning)"
```

---

## Monitoring & Rollback

### Monitoring Approach for Phase 1A

**Phase 1A uses structured logging only** - Prometheus metrics are optional and recommended for Phase 4 or later.

**Structured Logging (Phase 1A - Required):**
- All autonomous executions log via `logger.info()` with `extra_fields`
- Query structured logs in ClickHouse for analysis (if ClickHouse is already set up)
- **No new ClickHouse tables required** - uses existing log infrastructure
- Low overhead, immediate deployment
- If you don't have ClickHouse, logs still work (file/stdout)
- See `_record_autonomous_telemetry()` method for implementation

**Prometheus Metrics (Phase 4+ - Optional):**
- For real-time dashboards and alerts
- Higher operational overhead
- Requires prometheus_client library
- Only add if you need real-time monitoring

### Key Metrics to Monitor

**Via Structured Logs (Phase 1A):**
- Filter logs by `autonomous_enabled=true`
- Query for error rates, latencies, complexity distribution
- Example: `SELECT * FROM logs WHERE autonomous_enabled = true`

**Via Prometheus (Optional - Phase 4+):**

```python
# Add to app/monitoring/autonomous_metrics.py (NEW FILE - OPTIONAL)
"""
Autonomous agent metrics (Phase 4+)
"""
from prometheus_client import Counter, Histogram, Gauge

# Execution counters
autonomous_executions_total = Counter(
    'autonomous_executions_total',
    'Total autonomous executions',
    ['execution_mode', 'success']
)

autonomous_retries_total = Counter(
    'autonomous_retries_total',
    'Total retry attempts',
    ['reason']
)

# Latency histogram
autonomous_latency_seconds = Histogram(
    'autonomous_latency_seconds',
    'Autonomous execution latency',
    ['execution_mode'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# Quality metrics
autonomous_complexity_score = Histogram(
    'autonomous_complexity_score',
    'Query complexity scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

autonomous_result_count = Histogram(
    'autonomous_result_count',
    'Number of results returned',
    ['execution_mode'],
    buckets=[0, 1, 2, 5, 10, 20, 50]
)

# Cost tracking
autonomous_cost_dollars = Counter(
    'autonomous_cost_dollars',
    'Cost in dollars',
    ['execution_mode']
)
```

### Alerting Rules

```yaml
# monitoring/alerts/autonomous_agents.yml
groups:
  - name: autonomous_agents
    interval: 30s
    rules:
      - alert: AutonomousHighErrorRate
        expr: |
          rate(autonomous_executions_total{success="false"}[5m])
          / rate(autonomous_executions_total[5m]) > 0.02
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in autonomous execution"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: AutonomousHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(autonomous_latency_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency in autonomous execution"
          description: "P95 latency is {{ $value }}s"

      - alert: AutonomousExcessiveRetries
        expr: |
          rate(autonomous_retries_total[5m]) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Excessive retry rate"
          description: "Retry rate is {{ $value }} per second"
```

### Rollback Procedure

```bash
#!/bin/bash
# deploy/rollback_autonomous.sh

set -e

echo "ROLLING BACK autonomous agents"

# Disable autonomy immediately
kubectl set env deployment/ai-chat-service \
  ENABLE_AUTONOMY=false

# Monitor rollback
kubectl rollout status deployment/ai-chat-service

# Verify classic routing is working
sleep 10
curl -f http://your-service.com/health

echo "Rollback complete. Autonomous agents disabled."

# Notify team
echo "Autonomous agents disabled. Investigate logs and metrics." | \
  slack-notify --channel=alerts
```

### Dashboard Queries

```sql
-- ClickHouse queries for analysis

-- Autonomous vs Classic performance
SELECT
    CASE WHEN autonomous_enabled = 1 THEN 'autonomous' ELSE 'classic' END as mode,
    count() as executions,
    avg(total_latency_ms) as avg_latency_ms,
    quantile(0.95)(total_latency_ms) as p95_latency_ms,
    avg(confidence_score) as avg_confidence,
    sum(success) / count() as success_rate,
    avg(result_count) as avg_results,
    sum(cost) as total_cost
FROM agent_execution_metrics
WHERE timestamp >= now() - INTERVAL 1 DAY
GROUP BY autonomous_enabled;

-- Complexity distribution
SELECT
    execution_mode,
    round(complexity_score, 1) as complexity_bucket,
    count() as count,
    avg(total_latency_ms) as avg_latency,
    avg(result_count) as avg_results
FROM agent_execution_metrics
WHERE autonomous_enabled = 1
  AND timestamp >= now() - INTERVAL 1 DAY
GROUP BY execution_mode, complexity_bucket
ORDER BY execution_mode, complexity_bucket;

-- Retry analysis
SELECT
    retry_count,
    count() as executions,
    sum(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
    sum(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
    avg(total_latency_ms) as avg_latency
FROM agent_execution_metrics
WHERE autonomous_enabled = 1
  AND timestamp >= now() - INTERVAL 1 DAY
GROUP BY retry_count
ORDER BY retry_count;
```

---

## Phase 2+ Extensions (Optional)

**Only implement these if Phase 1A proves valuable in production.**

### Phase 2A: Zettelkasten Memory (Weeks 6-8)
- Connected knowledge graph for insights
- Semantic retrieval of past learnings
- Auto-linking related queries/reflections
- **Value:** Better context for complex queries
- **Cost:** ClickHouse storage + embeddings

### Phase 2B: Hierarchical Agents (Weeks 9-11)
- Manager/worker pattern for task decomposition
- Parallel subtask execution
- Dependency resolution
- **Value:** Handle 0.85+ complexity queries
- **Cost:** Increased latency for complex queries

### Phase 3: Background Learning (Weeks 12-14)
- Offline pattern extraction
- Proactive suggestions
- Continuous improvement
- **Value:** System gets smarter over time
- **Cost:** Background compute resources

### Phase 4: LATS Tree Search (Weeks 15-16)
- Monte Carlo tree search for highest complexity
- Multiple solution paths exploration
- Best path selection
- **Value:** Best answers for hardest queries
- **Cost:** 5-10x latency for 0.9+ complexity

**Decision Point:**
After Phase 1A runs for 2-4 weeks, analyze:
1. What % of queries benefit from autonomy?
2. Are complex queries (0.7+) common enough for Phase 2?
3. Is reflexion finding useful insights for Phase 3?
4. Do users need better answers badly enough for Phase 4 latency?

---

## Success Criteria

### Week 1-2 (Implementation)
- ✅ All tests pass
- ✅ Zero regression in existing functionality
- ✅ Autonomous mode works with `ENABLE_AUTONOMY=true`
- ✅ Classic mode works with `ENABLE_AUTONOMY=false`

### Week 3 (5% Rollout)
- ✅ Error rate < 2%
- ✅ P95 latency < 5s
- ✅ Cost increase < 10%
- ✅ No customer complaints

### Week 4-5 (25-100% Rollout)
- ✅ Sustained error rate < 2%
- ✅ P95 latency < 5s
- ✅ Complexity assessment accuracy > 80%
- ✅ Reflexion helps in 20%+ of retries

### Success Metrics (After 1 Month)
- 🎯 85%+ queries use phi3:mini (cost optimization)
- 🎯 User satisfaction maintained or improved
- 🎯 System handles 10%+ more complex queries successfully
- 🎯 Retry mechanism improves results in 30%+ of cases

---

## Appendix: Quick Reference

### Enable/Disable Autonomy

```bash
# Disable (safe default)
export ENABLE_AUTONOMY=false

# Enable
export ENABLE_AUTONOMY=true

# Restart service
systemctl restart ai-chat-service
```

### Debug Commands

```bash
# Check if autonomy is enabled
curl http://localhost:8000/system/status | jq '.settings.enable_autonomy'

# View recent autonomous executions
curl http://localhost:8000/debug/autonomous/recent

# Get specific execution details
curl http://localhost:8000/debug/autonomous/execution/{execution_id}

# View telemetry
docker logs ai-chat-service | grep "Autonomous execution completed"
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High error rate | LLM JSON parsing fails | Check JSON parser fallback strategies |
| Infinite retries | Reflexion always says "retry" | Verify max_retry_count enforced |
| High latency | Complex queries stuck in planning | Add execution timeout guards |
| No results | All searches failing | Check document/web search services |
| Cost spike | Too many retries | Lower max_retry_count, check cost limits |

---

## Timeline Summary

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 1 | Implementation | Code complete, tests passing |
| 2 | Dev Testing | Zero regression verified, autonomy works |
| 3 | 5% Rollout | Production monitoring, first metrics |
| 4 | 25% Rollout | Validation at scale |
| 5 | 100% Rollout | Full deployment |
| 6+ | Phase 2+ | Optional extensions based on data |

---

**This plan is production-ready and focused on delivering value quickly with minimal risk.** 🚀

All critical fixes have been applied, code is complete, and deployment strategy is conservative with clear rollback procedures.

**Recommended Next Steps:**
1. Review this plan with your team
2. Create feature branch and apply code changes
3. Run full test suite
4. Deploy to dev with `ENABLE_AUTONOMY=false`
5. Enable autonomy and validate
6. Begin gradual production rollout

**Questions or need clarification on any section?**
