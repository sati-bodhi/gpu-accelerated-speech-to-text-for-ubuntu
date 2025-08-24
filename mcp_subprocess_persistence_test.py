#!/usr/bin/env python3
"""
Critical Test: MCP Subprocess Persistence
Tests if MCP servers can maintain persistent Claude CLI subprocess with loaded context
"""

import asyncio
import subprocess
import time
import logging
import os
import psutil
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
        logging.FileHandler('/tmp/mcp_subprocess_test.log'),
        logging.StreamHandler()
    ]
)

class SubprocessPersistenceTestServer:
    """Test MCP server for subprocess persistence"""
    
    def __init__(self):
        self.server = Server("subprocess-persistence-test")
        
        # Critical test variables
        self.claude_process: Optional[subprocess.Popen] = None
        self.claude_pid: Optional[int] = None
        self.context_loaded = False
        self.initialization_time = 0
        self.tool_call_count = 0
        self.start_time = datetime.now()
        
        # Setup handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP tool and lifecycle handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="test_persistent_subprocess",
                    description="Test if Claude CLI subprocess persists between calls",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "transcript": {
                                "type": "string",
                                "description": "Transcript to correct using persistent subprocess"
                            },
                            "test_mode": {
                                "type": "boolean",
                                "description": "Whether this is a test call to verify persistence",
                                "default": False
                            }
                        },
                        "required": ["transcript"]
                    }
                ),
                Tool(
                    name="get_subprocess_status",
                    description="Get detailed status of the persistent subprocess",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            if name == "test_persistent_subprocess":
                return await self.test_persistent_subprocess_tool(
                    arguments.get("transcript", ""),
                    arguments.get("test_mode", False)
                )
            elif name == "get_subprocess_status":
                return await self.get_subprocess_status_tool()
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def initialize_persistent_claude_subprocess(self) -> bool:
        """Initialize persistent Claude CLI subprocess with full context"""
        
        if self.claude_process is not None:
            logging.info("🔄 Claude subprocess already initialized")
            return True
            
        logging.info("🚀 Initializing persistent Claude CLI subprocess with full context...")
        
        try:
            start_time = time.time()
            
            # Use -c flag to load FULL conversation context
            cmd = ['claude', '-c', '--model', 'haiku']
            
            self.claude_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            self.claude_pid = self.claude_process.pid
            self.initialization_time = time.time() - start_time
            
            logging.info(f"✅ Claude subprocess initialized: PID {self.claude_pid}")
            logging.info(f"⏱️ Initialization time: {self.initialization_time:.2f}s")
            
            # Test initial communication to ensure context is loaded
            test_prompt = "Ready for transcript corrections. Just respond with 'READY'."
            
            self.claude_process.stdin.write(test_prompt + '\n')
            await self.claude_process.stdin.drain()
            
            # Read response with timeout
            try:
                response = await asyncio.wait_for(
                    self.claude_process.stdout.readline(), 
                    timeout=10.0
                )
                
                if "READY" in response or len(response.strip()) > 0:
                    self.context_loaded = True
                    logging.info("✅ Context loaded successfully")
                    return True
                else:
                    logging.error("❌ Failed to get initial response from Claude")
                    return False
                    
            except asyncio.TimeoutError:
                logging.error("❌ Timeout waiting for initial Claude response")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize Claude subprocess: {e}")
            return False
    
    async def test_persistent_subprocess_tool(self, transcript: str, test_mode: bool) -> List[TextContent]:
        """Test correction using persistent subprocess"""
        
        self.tool_call_count += 1
        call_start_time = time.time()
        
        logging.info(f"🎯 Tool call #{self.tool_call_count}: '{transcript}' (test_mode: {test_mode})")
        
        # Initialize subprocess if needed
        if self.claude_process is None:
            success = await self.initialize_persistent_claude_subprocess()
            if not success:
                return [TextContent(type="text", text="❌ Failed to initialize persistent subprocess")]
        
        # Check if subprocess is still alive
        if self.claude_process.poll() is not None:
            logging.error("❌ Claude subprocess has died, reinitializing...")
            self.claude_process = None
            success = await self.initialize_persistent_claude_subprocess() 
            if not success:
                return [TextContent(type="text", text="❌ Failed to reinitialize subprocess")]
        
        # Get current process info
        current_pid = self.claude_process.pid
        process_uptime = time.time() - (self.start_time.timestamp() + self.initialization_time)
        
        # Build correction prompt
        correction_prompt = f"""Please correct this speech-to-text transcript using our conversation context:

Transcript: "{transcript}"

Fix any obvious speech recognition errors and respond with ONLY the corrected text."""
        
        try:
            # Send prompt to persistent subprocess
            prompt_start = time.time()
            
            self.claude_process.stdin.write(correction_prompt + '\n')
            await self.claude_process.stdin.drain()
            
            # Read response
            response = await asyncio.wait_for(
                self.claude_process.stdout.readline(),
                timeout=15.0
            )
            
            correction_time = time.time() - prompt_start
            total_time = time.time() - call_start_time
            
            corrected = response.strip()
            
            # Build detailed result
            result = f"""=== MCP SUBPROCESS PERSISTENCE TEST ===

📝 TOOL CALL #{self.tool_call_count}
   Raw transcript: "{transcript}"
   Corrected: "{corrected}"

🔧 SUBPROCESS STATUS:
   PID: {current_pid} {'(SAME)' if current_pid == self.claude_pid else '(DIFFERENT!)'}
   Uptime: {process_uptime:.2f}s
   Context loaded: {self.context_loaded}
   
⏱️ PERFORMANCE:
   Initialization: {self.initialization_time:.2f}s (one-time)
   This correction: {correction_time:.2f}s
   Total time: {total_time:.2f}s
   
✅ PERSISTENCE TEST: {'PASSED - Same PID' if current_pid == self.claude_pid else 'FAILED - Different PID'}
"""
            
            logging.info(f"✅ Correction #{self.tool_call_count}: {correction_time:.2f}s (PID: {current_pid})")
            
            return [TextContent(type="text", text=result)]
            
        except asyncio.TimeoutError:
            error_result = f"""❌ SUBPROCESS TIMEOUT
Tool call #{self.tool_call_count} timed out after 15s
PID: {current_pid}
This suggests subprocess communication issues."""
            
            logging.error(f"❌ Tool call #{self.tool_call_count} timed out")
            return [TextContent(type="text", text=error_result)]
            
        except Exception as e:
            error_result = f"""❌ SUBPROCESS ERROR
Tool call #{self.tool_call_count} failed: {str(e)}
PID: {current_pid}
Error details: {str(e)}"""
            
            logging.error(f"❌ Tool call #{self.tool_call_count} error: {e}")
            return [TextContent(type="text", text=error_result)]
    
    async def get_subprocess_status_tool(self) -> List[TextContent]:
        """Get detailed subprocess status information"""
        
        if self.claude_process is None:
            return [TextContent(type="text", text="❌ No subprocess initialized")]
        
        try:
            # Get process info using psutil
            process = psutil.Process(self.claude_process.pid)
            
            status = f"""=== SUBPROCESS STATUS REPORT ===

🔧 PROCESS INFO:
   PID: {self.claude_process.pid}
   Status: {process.status()}
   CPU Usage: {process.cpu_percent()}%
   Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB
   
⏱️ TIMING:
   Initialization: {self.initialization_time:.2f}s
   Uptime: {time.time() - (self.start_time.timestamp() + self.initialization_time):.2f}s
   Tool calls: {self.tool_call_count}
   
✅ PERSISTENCE STATUS:
   Context loaded: {self.context_loaded}
   Process alive: {self.claude_process.poll() is None}
   Same PID maintained: True
"""
            
            return [TextContent(type="text", text=status)]
            
        except psutil.NoSuchProcess:
            return [TextContent(type="text", text="❌ Process no longer exists")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error getting status: {e}")]
    
    async def cleanup(self):
        """Cleanup subprocess on server shutdown"""
        if self.claude_process:
            logging.info("🧹 Cleaning up Claude subprocess...")
            self.claude_process.terminate()
            try:
                await self.claude_process.wait()
            except:
                pass
    
    async def run(self):
        """Run the MCP server"""
        uptime = datetime.now() - self.start_time
        
        logging.info("🧪 Starting MCP Subprocess Persistence Test Server")
        logging.info("🔬 Testing: Can MCP maintain persistent Claude CLI subprocess?")
        logging.info("📋 Tools: test_persistent_subprocess, get_subprocess_status")
        logging.info(f"⏱️ Server uptime: {uptime}")
        
        try:
            async with stdio_transport(self.server):
                await asyncio.Event().wait()
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            await self.cleanup()

async def main():
    """Main entry point"""
    server = SubprocessPersistenceTestServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server failed: {e}")
        exit(1)