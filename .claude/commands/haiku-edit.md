---
description: Fix transcription errors and grammar issues in unclear speech-to-text output, then type the correction to your active window
allowed-tools: [Task, Bash]
model: haiku
---

This command will:
1. Use the haiku-edit-agent to correct transcription errors and grammar issues
2. Type the corrected text to your active window with " → [correction]" format
3. Provide immediate visual feedback of the correction

The agent fixes:
- Obvious transcription mistakes (e.g., "inscription" → "transcription")
- Basic grammar and syntax errors  
- Adds minimal context to clarify incomplete phrases
- Keeps corrections simple without over-elaborating

Usage: `/haiku-edit [unclear transcript text]`

Step 1: Get correction from haiku-edit-agent for: "$ARGUMENTS"

Step 2: After receiving the corrected text, use the typing script to display it visually.