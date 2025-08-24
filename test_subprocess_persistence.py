#!/usr/bin/env python3
"""
Test MCP Subprocess Persistence
Critical test to determine optimal architecture
"""

import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_mcp_subprocess_persistence():
    """Test if MCP server can maintain persistent Claude CLI subprocess"""
    
    logging.info("🧪 CRITICAL TEST: MCP Subprocess Persistence")
    logging.info("📋 Testing if same Claude subprocess persists across multiple tool calls")
    
    # Test sequence to verify persistence
    test_calls = [
        {
            "transcript": "how is our cuba container doing right now",
            "call_id": 1,
            "purpose": "Initial call - establishes subprocess"
        },
        {
            "transcript": "we need to test the haiku model performance", 
            "call_id": 2,
            "purpose": "Second call - should reuse same subprocess"
        },
        {
            "transcript": "the m c p server is working well",
            "call_id": 3, 
            "purpose": "Third call - verify continued persistence"
        }
    ]
    
    results = []
    
    for test in test_calls:
        logging.info(f"\n{'='*60}")
        logging.info(f"TEST CALL {test['call_id']}: {test['purpose']}")
        logging.info(f"Transcript: '{test['transcript']}'")
        
        # Build Claude CLI prompt to use MCP
        prompt = f"""Using the subprocess-persistence-test MCP server, test persistent subprocess:

Please use the test_persistent_subprocess tool with:
- transcript: "{test['transcript']}"
- test_mode: true

This will test if the Claude CLI subprocess maintains the same PID across calls."""
        
        # Call Claude CLI with MCP config
        cmd = [
            'claude',
            '--mcp-config', '/home/sati/speech-to-text-for-ubuntu/subprocess_test_mcp_config.json',
            '--model', 'haiku',
            '-p',
            prompt
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                logging.info(f"✅ Call {test['call_id']} completed in {elapsed:.2f}s")
                
                # Extract key information from result
                output = result.stdout
                
                # Look for PID information
                pid_info = "UNKNOWN"
                if "PID:" in output:
                    for line in output.split('\n'):
                        if "PID:" in line:
                            pid_info = line.strip()
                            break
                
                # Look for persistence status
                persistence_status = "UNKNOWN"
                if "PERSISTENCE TEST:" in output:
                    for line in output.split('\n'):
                        if "PERSISTENCE TEST:" in line:
                            persistence_status = line.strip()
                            break
                
                result_data = {
                    "call_id": test['call_id'],
                    "success": True,
                    "elapsed": elapsed,
                    "pid_info": pid_info,
                    "persistence_status": persistence_status,
                    "output_preview": output[:300] + "..." if len(output) > 300 else output
                }
                
                logging.info(f"📊 PID Info: {pid_info}")
                logging.info(f"🔧 Persistence: {persistence_status}")
                
            else:
                logging.error(f"❌ Call {test['call_id']} failed: {result.stderr}")
                result_data = {
                    "call_id": test['call_id'],
                    "success": False,
                    "error": result.stderr,
                    "elapsed": elapsed
                }
            
            results.append(result_data)
            
        except subprocess.TimeoutExpired:
            logging.error(f"❌ Call {test['call_id']} timed out after 45s")
            results.append({
                "call_id": test['call_id'],
                "success": False,
                "error": "Timeout",
                "elapsed": 45.0
            })
        except Exception as e:
            logging.error(f"❌ Call {test['call_id']} exception: {e}")
            results.append({
                "call_id": test['call_id'],
                "success": False,
                "error": str(e),
                "elapsed": 0
            })
    
    # Analyze results
    logging.info(f"\n{'='*60}")
    logging.info("📊 SUBPROCESS PERSISTENCE TEST ANALYSIS")
    
    successful_calls = [r for r in results if r.get('success')]
    
    if len(successful_calls) >= 2:
        logging.info(f"✅ {len(successful_calls)}/{len(test_calls)} calls successful")
        
        # Check if PIDs are consistent (indicating persistence)
        pids = []
        for result in successful_calls:
            pid_line = result.get('pid_info', '')
            if 'PID:' in pid_line and '(SAME)' in pid_line:
                logging.info(f"🎯 Call {result['call_id']}: Same PID maintained")
            elif 'PID:' in pid_line and '(DIFFERENT!)' in pid_line:
                logging.warning(f"⚠️ Call {result['call_id']}: Different PID - persistence failed")
        
        # Check persistence status
        all_persistent = all('PASSED' in r.get('persistence_status', '') for r in successful_calls)
        
        if all_persistent:
            logging.info("🎉 PERSISTENCE TEST RESULT: SUCCESS!")
            logging.info("✅ MCP servers CAN maintain persistent Claude CLI subprocesses")
            logging.info("🚀 RECOMMENDATION: Use full context + persistent subprocess architecture")
        else:
            logging.warning("⚠️ PERSISTENCE TEST RESULT: MIXED/FAILED")
            logging.info("🔄 RECOMMENDATION: Use limited context approach (99.8% token savings)")
            
    else:
        logging.error("❌ PERSISTENCE TEST RESULT: FAILED")
        logging.error("Too many call failures to determine persistence capability")
    
    # Performance summary
    if successful_calls:
        avg_time = sum(r['elapsed'] for r in successful_calls) / len(successful_calls)
        logging.info(f"⏱️ Average call time: {avg_time:.2f}s")
        
        if avg_time < 5:
            logging.info("⚡ Performance: EXCELLENT (sub-5s)")
        elif avg_time < 10:
            logging.info("✅ Performance: GOOD (5-10s)")
        else:
            logging.info("⚠️ Performance: SLOW (10s+)")

def test_status_tool():
    """Test the subprocess status tool"""
    logging.info(f"\n{'='*60}")
    logging.info("🔍 TESTING SUBPROCESS STATUS TOOL")
    
    prompt = """Using the subprocess-persistence-test MCP server, get subprocess status:

Please use the get_subprocess_status tool to show detailed information about the persistent subprocess."""
    
    cmd = [
        'claude',
        '--mcp-config', '/home/sati/speech-to-text-for-ubuntu/subprocess_test_mcp_config.json', 
        '--model', 'haiku',
        '-p',
        prompt
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logging.info("✅ Status tool successful")
            logging.info(f"Status info: {result.stdout[:500]}...")
        else:
            logging.error(f"❌ Status tool failed: {result.stderr}")
    except Exception as e:
        logging.error(f"❌ Status tool error: {e}")

if __name__ == "__main__":
    logging.info("🧪 Starting MCP Subprocess Persistence Critical Test")
    
    # Main persistence test
    test_mcp_subprocess_persistence()
    
    # Status tool test
    test_status_tool()
    
    logging.info("\n✅ Subprocess persistence testing completed")
    logging.info("📋 Check results above to determine optimal architecture")