#!/usr/bin/env python3
"""
Test Limited Context MCP Solution
Tests the token-efficient approach using recent conversation context
"""

import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_claude_cli_with_limited_context_mcp():
    """Test Claude CLI with limited context MCP"""
    
    test_cases = [
        {
            "transcript": "how is our cuba container doing right now",
            "confidence": 0.3,
            "expected": "CUDA container"  # Should correct based on our conversation context
        },
        {
            "transcript": "we need to fix the haiku model selection", 
            "confidence": 0.8,
            "expected": "haiku model"  # High confidence, should skip correction
        },
        {
            "transcript": "the m c p server is working well",
            "confidence": 0.4,
            "expected": "MCP server"  # Should correct based on context
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"TEST {i}: '{test_case['transcript']}' (confidence: {test_case['confidence']})")
        
        # Construct prompt for Claude CLI with MCP
        prompt = f"""Using the limited-context-correction MCP server, correct this transcript:

Please use the correct_transcript_with_limited_context tool with these parameters:
- raw_transcript: "{test_case['transcript']}"  
- confidence: {test_case['confidence']}
- context_exchanges: 3

The tool should use recent conversation context about CUDA, MCP, Haiku, etc. to make intelligent corrections."""
        
        # Call Claude CLI with MCP config
        cmd = [
            'claude',
            '--mcp-config', '/home/sati/speech-to-text-for-ubuntu/limited_context_mcp_config.json',
            '--model', 'haiku',
            '-p',
            prompt
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                logging.info(f"✅ Completed in {elapsed:.2f}s")
                logging.info(f"Result preview: {result.stdout[:200]}...")
                
                # Check if expected correction occurred
                if test_case['expected'].lower() in result.stdout.lower():
                    logging.info(f"🎯 Expected correction found: {test_case['expected']}")
                else:
                    logging.warning(f"⚠️ Expected correction not found: {test_case['expected']}")
                    
            else:
                logging.error(f"❌ Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.error("❌ Timeout after 30s")
        except Exception as e:
            logging.error(f"❌ Exception: {e}")

def test_context_parser_directly():
    """Test the context parser directly"""
    logging.info(f"\n{'='*60}")
    logging.info("TESTING CONTEXT PARSER DIRECTLY")
    
    try:
        from claude_context_parser import ClaudeContextParser
        
        parser = ClaudeContextParser()
        context = parser.get_context_for_transcript_correction(3)
        
        logging.info(f"Context length: {len(context)} characters")
        logging.info(f"Context tokens: ~{len(context.split())} tokens")
        logging.info(f"Context preview:\n{context}")
        
        # Test if context contains relevant technical terms
        relevant_terms = ['CUDA', 'MCP', 'Haiku', 'token', 'container']
        found_terms = [term for term in relevant_terms if term.lower() in context.lower()]
        
        logging.info(f"Relevant terms found: {found_terms}")
        
        if len(found_terms) >= 2:
            logging.info("✅ Context contains relevant technical terms")
        else:
            logging.warning("⚠️ Context may not have enough technical context")
            
    except Exception as e:
        logging.error(f"❌ Context parser error: {e}")

def compare_token_usage():
    """Compare expected token usage"""
    logging.info(f"\n{'='*60}")
    logging.info("TOKEN USAGE COMPARISON")
    
    # Current approach (full session context)
    current_tokens = 284000  # From user's evidence
    
    # Limited context approach
    context_tokens = 500  # ~3 exchanges
    prompt_tokens = 100   # Correction prompt
    response_tokens = 50  # Corrected transcript  
    limited_tokens = context_tokens + prompt_tokens + response_tokens
    
    savings = current_tokens - limited_tokens
    savings_percent = (savings / current_tokens) * 100
    
    logging.info(f"Current approach: {current_tokens:,} tokens per correction")
    logging.info(f"Limited context:  {limited_tokens:,} tokens per correction")
    logging.info(f"Savings:          {savings:,} tokens ({savings_percent:.1f}% reduction)")
    logging.info(f"Cost savings:     ~{savings_percent:.1f}% reduction in API costs")

if __name__ == "__main__":
    logging.info("🧪 Testing Limited Context MCP Solution")
    
    # Test context parser first
    test_context_parser_directly()
    
    # Compare expected token usage
    compare_token_usage()
    
    # Test Claude CLI with MCP (if available)
    test_claude_cli_with_limited_context_mcp()
    
    logging.info("\n✅ Testing completed")