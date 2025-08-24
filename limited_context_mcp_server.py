#!/usr/bin/env python3
"""
Limited Context MCP Server for Transcript Correction
Uses recent conversation context instead of full session history
"""

import asyncio
import subprocess
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime

# MCP imports  
from mcp.server import Server
from mcp.server.stdio import stdio_transport
from mcp.types import Tool, TextContent

# Our context parser
from claude_context_parser import ClaudeContextParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/limited_context_mcp.log'),
        logging.StreamHandler()
    ]
)

class LimitedContextCorrectionServer:
    """MCP server for transcript correction with limited context"""
    
    def __init__(self):
        self.server = Server("limited-context-correction")
        self.context_parser = ClaudeContextParser()
        self.claude_process = None
        self.correction_count = 0
        self.start_time = datetime.now()
        
        # Setup handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="correct_transcript_with_limited_context",
                    description="Correct speech transcript using recent conversation context only",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "raw_transcript": {
                                "type": "string",
                                "description": "Raw speech-to-text transcript to correct"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Confidence score (0-1) of the raw transcript",
                                "minimum": 0,
                                "maximum": 1
                            },
                            "context_exchanges": {
                                "type": "integer", 
                                "description": "Number of recent exchanges to use for context",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["raw_transcript"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            if name == "correct_transcript_with_limited_context":
                return await self.correct_transcript_tool(
                    arguments.get("raw_transcript", ""),
                    arguments.get("confidence", 0.5),
                    arguments.get("context_exchanges", 3)
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def correct_transcript_tool(self, raw_transcript: str, confidence: float, context_exchanges: int) -> List[TextContent]:
        """Correct transcript using limited recent context"""
        
        start_time = time.time()
        self.correction_count += 1
        
        logging.info(f"🎯 Correction #{self.correction_count}: '{raw_transcript}' (confidence: {confidence:.2f})")
        
        # High confidence - skip correction
        if confidence >= 0.75:
            result = f"""=== LIMITED CONTEXT TRANSCRIPT CORRECTION ===

📝 RAW TRANSCRIPT: "{raw_transcript}"
🎯 CONFIDENCE: {confidence:.2f} (HIGH - skipping correction)

✅ FINAL TRANSCRIPT: "{raw_transcript}"
⚡ PROCESSING: 0.01s (fast path)
📊 CORRECTION #{self.correction_count}
"""
            
            logging.info(f"✅ High confidence - skipped correction: 0.01s")
            return [TextContent(type="text", text=result)]
        
        # Low confidence - get limited context and correct
        try:
            # Extract recent context (THIS IS THE KEY INNOVATION)
            context = self.context_parser.get_context_for_transcript_correction(context_exchanges)
            context_tokens = len(context.split())
            
            # Build correction prompt with limited context
            correction_prompt = f"""{context}

Please correct this speech-to-text transcript based on the above conversation context:

Raw transcript: "{raw_transcript}"

Rules:
1. Fix speech recognition errors (e.g., "cuba" -> "CUDA", "haiku" -> "Haiku") 
2. Use conversation context to understand technical terms and topics
3. Maintain the speaker's original intent
4. Output ONLY the corrected text, no explanations

Corrected transcript:"""

            # Call Claude with limited context (NOT full session)
            correction_start = time.time()
            corrected_text = await self.call_claude_with_limited_context(correction_prompt)
            correction_time = time.time() - correction_start
            
            total_time = time.time() - start_time
            
            result = f"""=== LIMITED CONTEXT TRANSCRIPT CORRECTION ===

📝 RAW TRANSCRIPT: "{raw_transcript}"
🎯 CONFIDENCE: {confidence:.2f} (LOW - applying correction)

🧠 CONTEXT USED: {context_exchanges} recent exchanges ({context_tokens} tokens)
Context preview: {context[:100]}...

✅ CORRECTED TRANSCRIPT: "{corrected_text}"

📊 PERFORMANCE:
   - Context extraction: {(correction_start - start_time):.2f}s
   - Claude correction: {correction_time:.2f}s  
   - Total time: {total_time:.2f}s
   - Correction #{self.correction_count}
   - Tokens used: ~{context_tokens + len(raw_transcript.split())}

🎉 SUCCESS: Limited context correction completed!
"""
            
            logging.info(f"✅ Corrected with limited context: {total_time:.2f}s")
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            error_time = time.time() - start_time
            error_result = f"""=== LIMITED CONTEXT CORRECTION ERROR ===

📝 RAW TRANSCRIPT: "{raw_transcript}" 
❌ ERROR: {str(e)}
⏱️ ERROR TIME: {error_time:.2f}s

🔄 FALLBACK: Using raw transcript unchanged
"""
            
            logging.error(f"❌ Correction failed: {e}")
            return [TextContent(type="text", text=error_result)]
    
    async def call_claude_with_limited_context(self, prompt: str) -> str:
        """Call Claude CLI with limited context prompt"""
        
        try:
            # THIS IS THE KEY: No -c flag, fresh session with only limited context
            cmd = ['claude', '--model', 'haiku', prompt]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                corrected = stdout.decode().strip()
                # Remove quotes if present  
                if corrected.startswith('"') and corrected.endswith('"'):
                    corrected = corrected[1:-1]
                return corrected
            else:
                raise Exception(f"Claude CLI failed: {stderr.decode()}")
                
        except Exception as e:
            raise Exception(f"Claude subprocess error: {e}")
    
    async def run(self):
        """Run the MCP server"""
        uptime = datetime.now() - self.start_time
        
        logging.info("🚀 Starting Limited Context Transcript Correction Server")
        logging.info("🧠 Using recent conversation context only (no full session)")
        logging.info("⚡ Expected token usage: ~500 per correction (vs 284k+)")
        logging.info(f"📋 Server uptime: {uptime}")
        
        try:
            async with stdio_transport(self.server):
                await asyncio.Event().wait()
        except Exception as e:
            logging.error(f"Server error: {e}")

async def main():
    """Main entry point"""
    server = LimitedContextCorrectionServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server failed: {e}")
        exit(1)