#!/usr/bin/env python3
"""
Test script for MCP-based transcript correction
Tests both direct MCP and Claude CLI with MCP integration
"""

import subprocess
import time
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_claude_cli_with_mcp():
    """Test Claude CLI with MCP configuration"""
    
    test_transcripts = [
        ("how is our cuba container doing right now", 0.3),  # Should correct to CUDA
        ("we need to fix the haiku model selection", 0.8),  # High confidence, minimal correction
        ("the demon is running with base on model", 0.4),   # Should correct to daemon and base.en
        ("check the m c p server status", 0.5),              # Should correct to MCP
    ]
    
    for raw_transcript, confidence in test_transcripts:
        logging.info(f"\n{'='*60}")
        logging.info(f"Testing: '{raw_transcript}' (confidence: {confidence})")
        
        # Construct prompt for Claude CLI with MCP
        prompt = f"""
Using the transcript-correction MCP server, correct this transcript:

Raw transcript: "{raw_transcript}"
Confidence: {confidence}

Please use the correct_transcript tool to process this."""
        
        # Call Claude CLI with MCP config
        cmd = [
            'claude', 
            '--mcp-config', '/home/sati/speech-to-text-for-ubuntu/mcp_config.json',
            '--model', 'claude-3-5-haiku-20241022',
            '-p',
            prompt
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                logging.info(f"✅ Corrected in {elapsed:.2f}s")
                logging.info(f"Result: {result.stdout.strip()}")
            else:
                logging.error(f"❌ Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.error("❌ Timeout after 10s")
        except Exception as e:
            logging.error(f"❌ Exception: {e}")

def test_direct_mcp_call():
    """Test direct MCP server call (if running)"""
    
    logging.info("\n" + "="*60)
    logging.info("Testing direct MCP server connection...")
    
    # This would require the MCP server to be running
    # For now, we'll test with subprocess
    test_input = {
        "raw_transcript": "how is the cuba net library working",
        "confidence": 0.4
    }
    
    # Start MCP server and send test request
    # This is simplified - in production you'd use proper MCP client
    logging.info(f"Test input: {test_input}")
    
    # Expected output: "How is the CuDNN library working?"
    logging.info("Expected: 'How is the CuDNN library working?'")

if __name__ == "__main__":
    logging.info("🧪 Testing MCP-based Transcript Correction")
    
    # Test Claude CLI with MCP
    test_claude_cli_with_mcp()
    
    # Test direct MCP connection
    test_direct_mcp_call()
    
    logging.info("\n✅ Tests completed")