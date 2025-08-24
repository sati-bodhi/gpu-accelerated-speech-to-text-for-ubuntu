#!/usr/bin/env python3
"""
Direct Subprocess Persistence Test
Tests if we can maintain a persistent Claude CLI subprocess directly
"""

import asyncio
import subprocess
import time
import logging
import psutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

class DirectSubprocessTest:
    """Direct test of subprocess persistence without MCP"""
    
    def __init__(self):
        self.claude_process = None
        self.claude_pid = None
        self.initialization_time = 0
        
    async def initialize_persistent_claude(self):
        """Initialize persistent Claude CLI with full context"""
        
        logging.info("🚀 Initializing persistent Claude CLI subprocess...")
        
        try:
            start_time = time.time()
            
            # Start Claude CLI with full context loading
            cmd = ['claude', '-c', '--model', 'haiku']
            
            self.claude_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.claude_pid = self.claude_process.pid
            self.initialization_time = time.time() - start_time
            
            logging.info(f"✅ Claude subprocess started: PID {self.claude_pid}")
            logging.info(f"⏱️ Initialization: {self.initialization_time:.2f}s")
            
            # Test initial communication
            test_prompt = "Context loaded. Respond with just 'READY' to confirm.\n"
            
            self.claude_process.stdin.write(test_prompt.encode())
            await self.claude_process.stdin.drain()
            
            # Try to read response
            try:
                response = await asyncio.wait_for(
                    self.claude_process.stdout.readline(),
                    timeout=15.0
                )
                
                response_text = response.decode().strip()
                logging.info(f"📥 Initial response: '{response_text}'")
                
                if len(response_text) > 0:
                    logging.info("✅ Communication established")
                    return True
                else:
                    logging.error("❌ No response from Claude")
                    return False
                    
            except asyncio.TimeoutError:
                logging.error("❌ Timeout waiting for response")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize: {e}")
            return False
    
    async def test_correction(self, transcript: str, call_number: int):
        """Test transcript correction using persistent subprocess"""
        
        if self.claude_process is None:
            logging.error("❌ No subprocess initialized")
            return None
            
        # Check if process is still alive
        if self.claude_process.poll() is not None:
            logging.error("❌ Subprocess has died")
            return None
        
        logging.info(f"🎯 Test {call_number}: '{transcript}'")
        
        # Build correction prompt
        prompt = f"""Correct this transcript using our conversation context:

"{transcript}"

Respond with only the corrected text, no explanations.
"""
        
        try:
            start_time = time.time()
            
            # Send prompt
            self.claude_process.stdin.write(prompt.encode())
            await self.claude_process.stdin.drain()
            
            # Read response
            response = await asyncio.wait_for(
                self.claude_process.stdout.readline(),
                timeout=10.0
            )
            
            correction_time = time.time() - start_time
            corrected = response.decode().strip()
            
            # Get process info
            process = psutil.Process(self.claude_process.pid)
            
            result = {
                "call_number": call_number,
                "original": transcript,
                "corrected": corrected,
                "correction_time": correction_time,
                "pid": self.claude_process.pid,
                "same_pid": self.claude_process.pid == self.claude_pid,
                "process_status": process.status(),
                "memory_mb": process.memory_info().rss / 1024 / 1024
            }
            
            logging.info(f"✅ Test {call_number}: {correction_time:.2f}s")
            logging.info(f"📝 '{transcript}' → '{corrected}'")
            logging.info(f"🔧 PID: {self.claude_process.pid} ({'SAME' if result['same_pid'] else 'DIFFERENT!'})")
            
            return result
            
        except asyncio.TimeoutError:
            logging.error(f"❌ Test {call_number}: Timeout")
            return None
        except Exception as e:
            logging.error(f"❌ Test {call_number}: Error - {e}")
            return None
    
    async def cleanup(self):
        """Cleanup subprocess"""
        if self.claude_process:
            logging.info("🧹 Cleaning up subprocess...")
            self.claude_process.terminate()
            try:
                await self.claude_process.wait()
            except:
                pass

async def run_persistence_test():
    """Run the direct persistence test"""
    
    logging.info("🧪 DIRECT SUBPROCESS PERSISTENCE TEST")
    logging.info("📋 Testing if Python can maintain persistent Claude CLI subprocess")
    
    test = DirectSubprocessTest()
    
    # Initialize subprocess
    success = await test.initialize_persistent_claude()
    if not success:
        logging.error("❌ Failed to initialize - test aborted")
        return
    
    # Test multiple corrections
    test_transcripts = [
        "how is our cuba container doing right now",
        "we need to test the haiku model performance", 
        "the m c p server is working well",
        "check the token consumption and costs"
    ]
    
    results = []
    
    for i, transcript in enumerate(test_transcripts, 1):
        result = await test.test_correction(transcript, i)
        if result:
            results.append(result)
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Analyze results
    logging.info(f"\n{'='*60}")
    logging.info("📊 PERSISTENCE TEST ANALYSIS")
    
    if len(results) >= 2:
        # Check if all used same PID
        all_same_pid = all(r['same_pid'] for r in results)
        avg_time = sum(r['correction_time'] for r in results) / len(results)
        
        logging.info(f"✅ Successful corrections: {len(results)}/{len(test_transcripts)}")
        logging.info(f"🔧 Same PID maintained: {'YES' if all_same_pid else 'NO'}")
        logging.info(f"⏱️ Average correction time: {avg_time:.2f}s")
        
        if all_same_pid:
            logging.info("🎉 PERSISTENCE CONFIRMED!")
            logging.info("✅ Can maintain persistent Claude CLI subprocess with context")
            logging.info("🚀 OPTIMAL ARCHITECTURE: Full context + persistent subprocess")
            
            # Performance analysis
            fastest = min(r['correction_time'] for r in results)
            slowest = max(r['correction_time'] for r in results)
            
            logging.info(f"⚡ Performance range: {fastest:.2f}s - {slowest:.2f}s")
            
            if avg_time < 3:
                logging.info("🚀 EXCELLENT: Sub-3 second corrections with full context!")
            elif avg_time < 5:
                logging.info("✅ GOOD: Sub-5 second corrections")
            else:
                logging.info("⚠️ MODERATE: 5+ second corrections")
                
        else:
            logging.warning("⚠️ PERSISTENCE FAILED")
            logging.info("🔄 FALLBACK: Use limited context approach")
    else:
        logging.error("❌ TEST FAILED: Too few successful corrections")
    
    # Cleanup
    await test.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(run_persistence_test())
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    except Exception as e:
        logging.error(f"Test failed: {e}")
        exit(1)