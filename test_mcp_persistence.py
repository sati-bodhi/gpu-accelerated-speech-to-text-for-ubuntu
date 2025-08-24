#!/usr/bin/env python3
"""
Test MCP Server Persistence
Tests whether MCP servers maintain persistent state across tool calls
"""

import asyncio
import time
import logging
from typing import Dict, List
from datetime import datetime

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_transport
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP package not found. Run: pip install mcp")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/test_mcp_persistence.log'),
        logging.StreamHandler()
    ]
)

class PersistenceTestServer:
    """Test MCP server to verify persistence capabilities"""
    
    def __init__(self):
        self.server = Server("persistence-test")
        self.call_count = 0
        self.memory = {}  # Persistent memory
        self.claude_process = None  # Would hold persistent Claude subprocess
        self.start_time = datetime.now()
        
        # Setup handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="test_persistence",
                    description="Test if MCP server maintains state between calls",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Test message to store and retrieve"
                            }
                        },
                        "required": ["message"]
                    }
                ),
                Tool(
                    name="simulate_claude_call",
                    description="Simulate a persistent Claude CLI subprocess call",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Prompt to send to simulated Claude process"
                            }
                        },
                        "required": ["prompt"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            if name == "test_persistence":
                return await self.test_persistence_tool(arguments.get("message", ""))
            elif name == "simulate_claude_call":
                return await self.simulate_claude_call_tool(arguments.get("prompt", ""))
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def test_persistence_tool(self, message: str) -> List[TextContent]:
        """Test persistence by maintaining state between calls"""
        self.call_count += 1
        current_time = datetime.now()
        uptime = current_time - self.start_time
        
        # Store message in persistent memory
        self.memory[self.call_count] = {
            "message": message,
            "timestamp": current_time.isoformat(),
            "uptime": str(uptime)
        }
        
        # Build response showing persistence
        response = f"""=== MCP Persistence Test ===
Call #{self.call_count}
Server uptime: {uptime}
Your message: "{message}"

Previous calls stored in memory:"""
        
        for call_id, data in self.memory.items():
            response += f"\n  {call_id}. {data['message']} (at {data['uptime']})"
        
        response += f"\n\n✅ Server maintained state across {self.call_count} calls"
        
        logging.info(f"Persistence test call #{self.call_count}: {message}")
        
        return [TextContent(type="text", text=response)]
    
    async def simulate_claude_call_tool(self, prompt: str) -> List[TextContent]:
        """Simulate maintaining a persistent Claude CLI subprocess"""
        
        # In real implementation, this would maintain a persistent subprocess
        # For now, simulate with delay and persistent state
        
        if self.claude_process is None:
            logging.info("🔥 Starting persistent Claude CLI simulation...")
            self.claude_process = {
                "started_at": datetime.now(),
                "session_calls": 0,
                "context_loaded": True  # Simulate loaded context
            }
            startup_delay = 3  # Simulate initial startup
            await asyncio.sleep(startup_delay)
            
        else:
            startup_delay = 0  # No startup delay for subsequent calls
        
        # Simulate processing
        self.claude_process["session_calls"] += 1
        processing_delay = 0.5  # Fast processing since context already loaded
        await asyncio.sleep(processing_delay)
        
        # Build response
        uptime = datetime.now() - self.claude_process["started_at"]
        
        response = f"""=== Persistent Claude CLI Simulation ===
Prompt: "{prompt}"

Claude Process State:
  - Started: {self.claude_process['started_at'].strftime('%H:%M:%S')}
  - Uptime: {uptime}
  - Session calls: {self.claude_process['session_calls']}
  - Context loaded: {self.claude_process['context_loaded']}

Performance:
  - Startup delay: {startup_delay}s
  - Processing time: {processing_delay}s
  - Total time: {startup_delay + processing_delay}s

✅ Simulated correction: "{prompt.replace('cuba', 'CUDA').replace('haiku', 'Haiku')}"
"""
        
        logging.info(f"Claude simulation call #{self.claude_process['session_calls']}: {processing_delay}s")
        
        return [TextContent(type="text", text=response)]
    
    async def run(self):
        """Run the MCP server"""
        logging.info("🚀 Starting MCP Persistence Test Server")
        logging.info("📋 Tools available: test_persistence, simulate_claude_call")
        
        try:
            async with stdio_transport(self.server):
                await asyncio.Event().wait()
        except Exception as e:
            logging.error(f"Server error: {e}")

async def main():
    """Main entry point"""
    server = PersistenceTestServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server failed: {e}")
        exit(1)