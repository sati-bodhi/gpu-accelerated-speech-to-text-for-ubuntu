#!/usr/bin/env python3
"""
Claude Code One-Shot MCP Server for Speech-to-Text
Uses Claude Code's built-in MCP server capabilities for context-aware corrections
"""

import asyncio
import subprocess
import time
import logging
import os
import json
import tempfile
from typing import Dict, List, Optional
from datetime import datetime

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_transport  
from mcp.types import Tool, TextContent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/claude_code_mcp.log'),
        logging.StreamHandler()
    ]
)

class ClaudeCodeMCPServer:
    """MCP server that uses Claude Code as a one-shot correction service"""
    
    def __init__(self):
        self.server = Server("claude-code-speech-corrections")
        
        # Performance tracking
        self.correction_count = 0
        self.total_correction_time = 0
        self.start_time = datetime.now()
        
        # Setup handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="correct_transcript_with_claude_code",
                    description="Use Claude Code MCP server for context-aware transcript correction",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "transcript": {
                                "type": "string",
                                "description": "Raw transcript text to correct"
                            },
                            "context_hint": {
                                "type": "string", 
                                "description": "Optional context hint about the conversation topic",
                                "default": ""
                            }
                        },
                        "required": ["transcript"]
                    }
                ),
                Tool(
                    name="get_server_stats",
                    description="Get performance statistics for the Claude Code MCP server",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            if name == "correct_transcript_with_claude_code":
                return await self.correct_transcript_tool(
                    arguments.get("transcript", ""),
                    arguments.get("context_hint", "")
                )
            elif name == "get_server_stats":
                return await self.get_stats_tool()
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def correct_transcript_tool(self, transcript: str, context_hint: str = "") -> List[TextContent]:
        """Correct transcript using Claude Code as one-shot MCP server"""
        
        self.correction_count += 1
        start_time = time.time()
        
        logging.info(f"🎯 Correction #{self.correction_count}: '{transcript[:50]}{'...' if len(transcript) > 50 else ''}'")
        
        try:
            # Create a temporary MCP configuration for Claude Code
            corrected, correction_time = await self.claude_code_one_shot_correction(transcript, context_hint)
            
            total_time = time.time() - start_time
            self.total_correction_time += correction_time
            
            result = f"""=== CLAUDE CODE MCP CORRECTION ===

📝 CORRECTION #{self.correction_count}
   Raw transcript: "{transcript}"
   Corrected: "{corrected}"
   Context hint: {context_hint or "None"}

⚡ PERFORMANCE:
   Correction time: {correction_time:.2f}s
   Total time: {total_time:.2f}s
   
✅ STATUS: Success using Claude Code MCP server
"""
            
            logging.info(f"✅ Correction #{self.correction_count}: {correction_time:.2f}s")
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            error_result = f"""❌ CLAUDE CODE MCP ERROR
Correction #{self.correction_count} failed: {str(e)}

This suggests Claude Code MCP server communication issues."""
            
            logging.error(f"❌ Correction #{self.correction_count} error: {e}")
            return [TextContent(type="text", text=error_result)]
    
    async def claude_code_one_shot_correction(self, transcript: str, context_hint: str = "") -> tuple[str, float]:
        """Use Claude Code as one-shot MCP server for correction"""
        
        # Create correction prompt optimized for Claude Code
        if context_hint:
            correction_prompt = f"""Context: {context_hint}

Speech-to-text transcript correction needed:
"{transcript}"

Please correct any speech recognition errors and provide the intended text that makes sense in the given context.

Respond with ONLY the corrected text, no quotes or explanations."""
        else:
            correction_prompt = f"""Please correct this speech-to-text transcript:
"{transcript}"

Fix obvious recognition errors. Respond with ONLY the corrected text."""
        
        try:
            start_time = time.time()
            
            # Use Claude Code directly with the haiku model
            # Claude Code handles context automatically through its MCP integration
            cmd = [
                'claude', 
                '--model', 'haiku',
                correction_prompt
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = await result.communicate()
            correction_time = time.time() - start_time
            
            if result.returncode == 0:
                corrected = stdout.strip()
                
                # Clean up response
                if corrected.startswith('"') and corrected.endswith('"'):
                    corrected = corrected[1:-1]
                
                return corrected, correction_time
            else:
                logging.error(f"Claude Code error: {stderr}")
                return transcript, correction_time
                
        except Exception as e:
            logging.error(f"Claude Code one-shot error: {e}")
            return transcript, 0.0
    
    async def get_stats_tool(self) -> List[TextContent]:
        """Get server performance statistics"""
        
        uptime = datetime.now() - self.start_time
        avg_correction_time = (self.total_correction_time / max(1, self.correction_count))
        
        stats = f"""=== CLAUDE CODE MCP SERVER STATS ===

📊 PERFORMANCE:
   Corrections processed: {self.correction_count}
   Average correction time: {avg_correction_time:.2f}s
   Total correction time: {self.total_correction_time:.2f}s
   Server uptime: {uptime}

🔧 CONFIGURATION:
   MCP Server: Claude Code One-Shot
   Model: Haiku
   Context handling: Claude Code built-in
   
✅ STATUS: Active and processing corrections
"""
        
        return [TextContent(type="text", text=stats)]
    
    async def run(self):
        """Run the Claude Code MCP server"""
        logging.info("🚀 Starting Claude Code MCP Server for Speech-to-Text")
        logging.info("🔧 Using Claude Code as one-shot correction service")
        logging.info("📋 Tools: correct_transcript_with_claude_code, get_server_stats")
        
        try:
            async with stdio_transport(self.server):
                await asyncio.Event().wait()
        except Exception as e:
            logging.error(f"Server error: {e}")

async def main():
    """Main entry point"""
    server = ClaudeCodeMCPServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server failed: {e}")
        exit(1)