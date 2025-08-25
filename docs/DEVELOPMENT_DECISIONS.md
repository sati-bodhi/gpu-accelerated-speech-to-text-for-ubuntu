# Development Decisions & Technical Rationale

## Overview

This document chronicles the optimization journey for the speech-to-text system, including major architectural decisions, critical issues encountered, and performance trade-offs discovered.

## Initial Problem: Token Consumption Crisis

**Root Issue**: Each Claude CLI call with `-c` flag reloaded entire conversation context
- **Token consumption**: 284,121+ tokens per correction
- **Cost impact**: $339.32+ per session  
- **Performance impact**: 15+ second correction times

**Example of the crisis**:
```bash
# Each correction call loads full conversation history
claude -c --model haiku "correct this transcript..."
# = 284,121 tokens × $1.20/1000 tokens = $339.32
```

## Current Architecture (Post-Rollback)

### Key Listener Flow
```
INSERT key press → arecord → speech_to_text_parallel.py → Claude CLI → pyautogui typing
```

**Components**:
1. **key_listener_pynput.py**: X11 key listener (INSERT key trigger)
2. **speech_to_text_parallel.py**: Parallel processing with model caching
3. **Claude CLI**: Full context correction using `-c` flag

**Current Status**: 
- ✅ **Works reliably** with high accuracy
- ❌ **284k token consumption** per correction
- ❌ **Cold model loading** (~2-3 seconds startup)

## Architecture Attempts & Issues

### 1. MCP Subprocess Persistence (FAILED)

**Goal**: Maintain persistent Claude CLI subprocess with loaded context

**Implementation Attempts**:
- MCP server with stdio transport
- Direct subprocess management
- FastMCP framework integration

**Failure Reason**: Claude CLI not designed for programmatic stdin/stdout communication
- Timeouts on subprocess communication
- No persistent session support
- Interactive terminal assumptions

**Code Evidence**: `mcp_subprocess_persistence_test.py` shows timeout failures

### 2. Limited Context Approach (PROBLEMATIC)

**Goal**: Extract recent conversation exchanges for 99.8% token reduction

**Implementation**: `claude_context_parser.py`
- Parses `~/.claude/projects/*/conversation.jsonl`
- Extracts last 3 user-assistant exchanges
- Builds minimal context prompt

**Token Reduction**: 284,121 → ~650 tokens (99.8% reduction)

#### Critical Issues Discovered

##### A. Context Extraction Failures

**Workspace Detection Problems**:
```python
# Problematic heuristic mapping
cwd = "/home/sati/speech-to-text-for-ubuntu"  
workspace = cwd.replace('/', '-')  # "home-sati-speech-to-text-for-ubuntu"
```

**Cross-Workspace Contamination**:
```python
# Fallback grabs ANY recent conversation
all_workspaces = glob.glob("/home/sati/.claude/projects/*/")
latest_file = max(recent_files, key=os.path.getmtime)  # WRONG CONTEXT!
```

**Real-World Failure**:
- Speech correction runs from speech-to-text project
- Expected workspace doesn't exist or has no conversations  
- System grabs conversation from **completely different project** (e.g., web development, documentation)
- Speech correction gets **irrelevant context** about unrelated topics
- Results in poor corrections due to domain mismatch

##### B. Technical Terminology Accuracy Problems

**Test Case Failure**:
```
Raw transcript: "Sting enhanced transcript correction system with High Cool model Doesn't seem to be working as well as with the C flag"

Limited context correction: Failed to identify technical terms
- "sea flag" should be "-c flag" 
- "High Cool model" should be "Haiku model"
```

**Root Cause**: Limited context lacks domain knowledge that full conversation provides

##### C. Reliability vs Cost Trade-off

**Fundamental tension**:
- **Full context** (`-c` flag): Accurate but 284k tokens = $339+
- **Limited context** (3 exchanges): 99.8% cheaper but unreliable

**User feedback**: *"If we fall back on the safe path and the persistence issue is not fixed, we get token explosion"*

### 3. Daemon Architecture (BUILT BUT UNUSED)

**Implementation**: `speech_daemon.py`
- Persistent Whisper model loading (~400MB RAM)
- Limited context integration
- Queue-based processing
- File-based client API

**Status**: 
- ✅ **Fully implemented** with optimizations
- ❌ **Not integrated** with key listener
- ❌ **Limited context issues** still present

**Integration Gap**: Listener still calls standalone script, missing all daemon benefits

## Performance Comparison

| Approach | Speed | Accuracy | Token Cost | Status |
|----------|--------|----------|------------|---------|
| **Current (Parallel + Full Context)** | 3-5s | High | 284k tokens | ✅ Working |
| **Limited Context** | 2-3s | Poor* | 650 tokens | ❌ Unreliable |
| **Daemon + Limited Context** | <1s | Poor* | 650 tokens | ⚠️ Not integrated |
| **MCP Persistence** | <1s | High | 284k tokens | ❌ Failed |

*Poor accuracy due to context extraction failures and technical terminology issues

## Current Implementation Status

### Working Components
- **key_listener_pynput.py**: ✅ Reliable X11 key capture
- **speech_to_text_parallel.py**: ✅ Model caching, ThreadPoolExecutor optimization
- **claude_context_parser.py**: ⚠️ Works but has reliability issues

### Problematic Components  
- **Context extraction**: Workspace detection and cross-contamination issues
- **Limited context accuracy**: Technical terminology failures
- **Token optimization**: No working solution for cost reduction

### Unused/Incomplete Components
- **speech_daemon.py**: Built but not integrated with listener
- **MCP server implementations**: Failed due to Claude CLI limitations

## Architectural Decisions Made

### Git Rollback Decision
**User request**: *"let's rollback a bit (with git) and keep the parallel processing and limited context implementations separate"*

**Implementation**:
- Rolled back `speech_to_text_parallel.py` to clean parallel processing
- Fixed `-p` flag issues (changed to `--model haiku`)  
- Separated concerns: accuracy-focused vs cost-optimized approaches

### Separation Strategy
- **Parallel processing**: High accuracy, high cost
- **Limited context**: Low cost, reliability issues
- **Daemon**: Performance optimization, not integrated

## Recommendations

### Immediate Actions
1. **Fix context extraction reliability**:
   - Improve workspace detection logic
   - Add conversation validation
   - Prevent cross-workspace contamination

2. **Complete separation**:
   - Create `speech_to_text_limited_context.py`
   - Test implementations independently
   - Allow clean choice between approaches

### Long-term Architecture
1. **Daemon Integration**: 
   - Connect listener to daemon for performance
   - Maintain separated correction approaches

2. **Context Strategy Improvement**:
   - Better workspace mapping
   - Domain-aware context selection
   - Technical terminology dictionary

3. **Cost Optimization Research**:
   - Alternative to full context loading
   - Smarter context filtering
   - Model-specific optimizations

## Technical Lessons Learned

1. **Claude CLI Limitations**: Not suitable for programmatic persistence
2. **Context Extraction Complexity**: Workspace detection is error-prone
3. **Accuracy vs Cost Trade-off**: No simple solution for both
4. **Reliability Requirements**: Speech systems need consistent accuracy
5. **Architecture Separation**: Critical for managing complexity

## Files and Code References

- `key_listener_pynput.py:33` - Script configuration
- `speech_to_text_parallel.py:105` - Claude CLI call with `-c` flag
- `claude_context_parser.py:57-95` - Conversation file detection
- `speech_daemon.py:182-238` - Limited context implementation  
- `mcp_subprocess_persistence_test.py` - Failed persistence attempts

---

*Last updated: 2025-08-23*
*Status: Post-rollback, clean implementations separated*