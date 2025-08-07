# Expert Agents Usage Guide: SearchGod and ChatGod

## Overview

Since Claude Code's Task tool only supports built-in agent types (general-purpose, ux-design-researcher, product-intelligence), we implement SearchGod and ChatGod as specialized prompts that can be used with the general-purpose agent.

## Implementation Approach

### 1. Using Python Script for Structured Prompts

```bash
# Generate SearchGod prompt for performance analysis
python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py searchgod \
  "Analyze current Ultra-Fast search performance and recommend GPU acceleration strategy"

# Generate ChatGod prompt for UX analysis  
python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py chatgod \
  "Review conversation flow and recommend voice interface integration approach"

# Generate collaboration prompt
python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py collaborate \
  "Create unified optimization plan based on search and chat analysis"
```

### 2. Direct Invocation with General-Purpose Agent

```bash
# SearchGod Analysis
claude-code task --agent general-purpose "$(python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py searchgod 'Analyze current search system performance and identify top 3 optimization opportunities')"

# ChatGod Analysis
claude-code task --agent general-purpose "$(python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py chatgod 'Analyze chat conversation patterns and recommend UX improvements')"
```

### 3. Manual Invocation in Claude Sessions

When working in a Claude session, you can invoke the expert agents by using their specialized prompts:

**For SearchGod Analysis:**
```
Act as SearchGod, an advanced search technology expert. Analyze the unified AI search system at /home/ews/unified-ai-system-clean/ and provide recommendations for:
1. GPU acceleration implementation
2. Performance optimization to achieve <50ms P99 latency
3. GraphRAG integration strategy

Include specific technical details, performance metrics, and implementation steps.
```

**For ChatGod Analysis:**
```
Act as ChatGod, a conversational AI expert. Review the chat service at /home/ews/unified-ai-system-clean/ai-chat-service/ and recommend:
1. Voice interface integration approach
2. Conversation flow optimizations
3. Context management improvements

Focus on user experience with measurable improvement targets.
```

## Automated Daily Research Workflow

Create a cron job for automated analysis:

```bash
# Add to crontab
0 9 * * * /home/ews/unified-ai-system-clean/scripts/daily_expert_analysis.sh
```

**daily_expert_analysis.sh:**
```bash
#!/bin/bash
# Daily expert agent analysis

DATE=$(date +%Y%m%d)
REPORT_DIR="/home/ews/unified-ai-system-clean/agent_reports/$DATE"
mkdir -p "$REPORT_DIR"

# SearchGod morning analysis
echo "Running SearchGod analysis..."
claude-code task --agent general-purpose "$(python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py searchgod 'Perform daily search system analysis including overnight performance metrics, latest ArXiv research, and competitive intelligence')" > "$REPORT_DIR/searchgod_analysis.md"

# ChatGod UX analysis
echo "Running ChatGod analysis..."
claude-code task --agent general-purpose "$(python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py chatgod 'Analyze daily chat metrics, user satisfaction scores, and conversation patterns to identify improvement opportunities')" > "$REPORT_DIR/chatgod_analysis.md"

# Collaboration synthesis
echo "Running collaboration synthesis..."
claude-code task --agent general-purpose "$(python /home/ews/unified-ai-system-clean/scripts/expert_agent_prompts.py collaborate 'Synthesize SearchGod and ChatGod findings into unified optimization plan')" > "$REPORT_DIR/collaboration_plan.md"

echo "Daily analysis complete. Reports saved to $REPORT_DIR"
```

## Key Differences from Original Vision

1. **Not True Agents**: SearchGod and ChatGod are implemented as specialized prompts, not independent agents
2. **Manual Invocation**: Requires explicit prompt generation and invocation through general-purpose agent
3. **No Direct Integration**: Cannot be called directly with `--agent search-expert` syntax
4. **Stateless Operation**: Each invocation is independent, no persistent agent state

## Practical Usage Examples

### Example 1: GPU Acceleration Research
```bash
# Generate comprehensive GPU analysis
python scripts/expert_agent_prompts.py searchgod \
  "Research NVIDIA cuVS/CAGRA implementation for our vector search. \
   Compare with current CPU performance, estimate implementation effort, \
   and provide step-by-step integration guide"
```

### Example 2: Voice Interface Planning
```bash
# Voice UX analysis
python scripts/expert_agent_prompts.py chatgod \
  "Design voice interface integration plan including: \
   1) OpenAI Whisper vs Azure Speech comparison \
   2) Conversation flow adaptations for voice \
   3) Mobile-first voice UX patterns"
```

### Example 3: Weekly Strategic Review
```bash
# Comprehensive system review
python scripts/expert_agent_prompts.py collaborate \
  "Conduct weekly strategic review incorporating: \
   - Performance trends from last 7 days \
   - Competitive landscape changes \
   - Resource allocation recommendations \
   - Updated roadmap priorities"
```

## Benefits of This Approach

1. **Structured Analysis**: Consistent expert-level analysis format
2. **Flexible Integration**: Can be used in scripts, cron jobs, or manual sessions
3. **Domain Expertise**: Specialized prompts ensure focused, relevant analysis
4. **Actionable Output**: Structured deliverables with specific recommendations

## Limitations

1. **No Persistent State**: Each analysis starts fresh without memory of previous runs
2. **Manual Orchestration**: Requires explicit invocation rather than autonomous operation  
3. **No Real-Time Monitoring**: Cannot continuously monitor system like true agents would
4. **Limited Tool Access**: Operates within general-purpose agent constraints

## Conclusion

While not true autonomous agents, these expert prompt templates provide a practical way to get specialized analysis from Claude for your unified AI search system. The structured prompts ensure consistent, high-quality analysis that aligns with the SearchGod and ChatGod personas described in your strategic documents.