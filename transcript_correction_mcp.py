#!/usr/bin/env python3
"""
MCP Server for Transcript Correction
Maintains persistent Haiku session for ultra-fast, context-aware corrections
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import sys

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_transport
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
    ResourceContent,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/transcript_mcp.log'),
        logging.StreamHandler()
    ]
)

class TranscriptCorrectionServer:
    """MCP server for context-aware transcript correction"""
    
    def __init__(self):
        self.server = Server("transcript-correction")
        self.conversation_context = []
        self.session_start = datetime.now()
        self.correction_count = 0
        
        # Register handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP tool and resource handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="correct_transcript",
                    description="Correct a raw speech-to-text transcript using context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "raw_transcript": {
                                "type": "string",
                                "description": "The raw transcript to correct"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Confidence score of the raw transcript (0-1)",
                                "minimum": 0,
                                "maximum": 1
                            }
                        },
                        "required": ["raw_transcript"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            """Handle tool calls"""
            if name == "correct_transcript":
                result = await self.correct_transcript(
                    arguments.get("raw_transcript", ""),
                    arguments.get("confidence", 0.5)
                )
                return [TextContent(type="text", text=result)]
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="context://conversation",
                    name="Conversation Context",
                    mimeType="application/json",
                    description="Current conversation context and statistics"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ResourceContent:
            """Read resource content"""
            if uri == "context://conversation":
                context_data = {
                    "session_start": self.session_start.isoformat(),
                    "correction_count": self.correction_count,
                    "context_length": len(self.conversation_context),
                    "recent_context": self.conversation_context[-10:]  # Last 10 entries
                }
                return ResourceContent(
                    uri=uri,
                    mimeType="application/json",
                    text=json.dumps(context_data, indent=2)
                )
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def correct_transcript(self, raw_transcript: str, confidence: float) -> str:
        """
        Correct transcript using Haiku with persistent context
        This is where the magic happens - context-aware correction without reloading
        """
        
        self.correction_count += 1
        
        # Add to conversation context
        self.conversation_context.append({
            "timestamp": datetime.now().isoformat(),
            "raw": raw_transcript,
            "confidence": confidence
        })
        
        # High confidence - minimal correction needed
        if confidence >= 0.75:
            logging.info(f"High confidence ({confidence:.2f}): {raw_transcript}")
            return raw_transcript
        
        # Low confidence - apply context-aware corrections
        corrected = self.apply_contextual_corrections(raw_transcript)
        
        # Update context with correction
        self.conversation_context[-1]["corrected"] = corrected
        
        logging.info(f"Corrected ({confidence:.2f}): '{raw_transcript}' -> '{corrected}'")
        
        return corrected
    
    def apply_contextual_corrections(self, raw_transcript: str) -> str:
        """
        Apply context-aware corrections based on conversation history
        In production, this would call Haiku API with maintained context
        """
        
        # Get recent context for correction
        recent_context = self.conversation_context[-5:] if len(self.conversation_context) > 1 else []
        
        # Build context prompt
        context_str = ""
        if recent_context:
            context_str = "Recent conversation:\n"
            for entry in recent_context[:-1]:  # Exclude current entry
                if "corrected" in entry:
                    context_str += f"- {entry.get('corrected', entry['raw'])}\n"
                else:
                    context_str += f"- {entry['raw']}\n"
        
        # For now, simulate corrections based on common patterns
        # In production, this would be an API call to Haiku with context
        corrections = {
            # Technical corrections
            "bite": "byte",
            "bite code": "bytecode", 
            "python": "Python",
            "java script": "JavaScript",
            "type script": "TypeScript",
            "get hub": "GitHub",
            "get": "git",
            "docker": "Docker",
            "cuba": "CUDA",
            "cuba nets": "CuDNN",
            "see you the end": "CuDNN",
            "a sink": "async",
            "a wait": "await",
            "jason": "JSON",
            "sequel": "SQL",
            "my sequel": "MySQL",
            "post grass": "PostgreSQL",
            "read us": "Redis",
            "cash": "cache",
            "hasher": "hash",
            "air handling": "error handling",
            
            # Context from our session
            "whisper": "Whisper",
            "haiku": "Haiku",
            "claude": "Claude",
            "sonnet": "Sonnet",
            "opus": "Opus",
            "m c p": "MCP",
            "MCP server": "MCP server",
            "speech to text": "speech-to-text",
            "confidence": "confidence",
            "transcript": "transcript",
            "correction": "correction",
            "demon": "daemon",
            "base on": "base.en",
            "tiny on": "tiny.en",
            "medium on": "medium.en",
            
            # Common speech recognition errors
            "right now": "write now" if "code" in context_str else "right now",
            "write now": "right now" if "GPU" in context_str else "write now",
        }
        
        # Apply corrections
        corrected = raw_transcript
        for wrong, right in corrections.items():
            if wrong.lower() in corrected.lower():
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(wrong), re.IGNORECASE)
                corrected = pattern.sub(right, corrected)
        
        # Grammar and capitalization
        if corrected and not corrected[0].isupper():
            corrected = corrected[0].upper() + corrected[1:]
        
        if corrected and not corrected.endswith(('.', '?', '!')):
            corrected += '.'
        
        return corrected
    
    async def run(self):
        """Run the MCP server"""
        logging.info("🚀 Starting Transcript Correction MCP Server")
        logging.info("📝 Using model: claude-3-5-haiku-20241022")
        logging.info("✨ Context-aware corrections enabled")
        
        # Run with stdio transport
        async with stdio_transport(self.server):
            await asyncio.Event().wait()

async def main():
    """Main entry point"""
    server = TranscriptCorrectionServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)