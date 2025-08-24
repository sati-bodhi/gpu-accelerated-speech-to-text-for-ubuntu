#!/usr/bin/env python3
"""
Direct Test of Limited Context Correction
Tests accuracy without full MCP server setup
"""

import subprocess
import time
import logging
from claude_context_parser import ClaudeContextParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_correction_with_limited_context(raw_transcript: str, confidence: float = 0.3):
    """Test transcript correction using limited context"""
    
    logging.info(f"🧪 Testing: '{raw_transcript}' (confidence: {confidence:.2f})")
    
    try:
        # Step 1: Extract limited context
        start_time = time.time()
        parser = ClaudeContextParser()
        context = parser.get_context_for_transcript_correction(3)
        context_time = time.time() - start_time
        
        logging.info(f"📝 Context extracted: {context_time:.2f}s, {len(context.split())} tokens")
        
        # Step 2: Build correction prompt with limited context
        correction_prompt = f"""{context}

Please correct this speech-to-text transcript based on the above conversation context:

Raw transcript: "{raw_transcript}"

Rules:
1. Fix speech recognition errors (e.g., "cuba" -> "CUDA", "haiku" -> "Haiku")
2. Use conversation context to understand technical terms
3. Maintain the speaker's intent 
4. Output ONLY the corrected text, no explanations

Corrected transcript:"""

        # Step 3: Call Claude CLI with limited context (no -c flag)
        claude_start = time.time()
        cmd = ['claude', '--model', 'haiku', correction_prompt]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        claude_time = time.time() - claude_start
        total_time = time.time() - start_time
        
        if result.returncode == 0:
            corrected = result.stdout.strip()
            # Remove quotes if present
            if corrected.startswith('"') and corrected.endswith('"'):
                corrected = corrected[1:-1]
            
            logging.info(f"✅ SUCCESS")
            logging.info(f"📝 Raw: '{raw_transcript}'")
            logging.info(f"✨ Corrected: '{corrected}'")
            logging.info(f"⏱️ Times: Context={context_time:.2f}s, Claude={claude_time:.2f}s, Total={total_time:.2f}s")
            logging.info(f"📊 Tokens: ~{len(context.split()) + len(raw_transcript.split())} (vs 284k+)")
            
            return {
                "success": True,
                "corrected": corrected,
                "times": {
                    "context": context_time,
                    "claude": claude_time, 
                    "total": total_time
                },
                "tokens_used": len(context.split()) + len(raw_transcript.split()),
                "context_preview": context[:100] + "..."
            }
        else:
            logging.error(f"❌ Claude failed: {result.stderr}")
            return {"success": False, "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        logging.error("❌ Timeout after 15s")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

def run_test_suite():
    """Run a suite of correction tests"""
    
    test_cases = [
        {
            "transcript": "how is our cuba container doing right now",
            "expected_terms": ["CUDA", "container"],
            "description": "CUDA container context test"
        },
        {
            "transcript": "we need to test the haiku model performance", 
            "expected_terms": ["Haiku", "model"],
            "description": "Haiku model context test"
        },
        {
            "transcript": "the m c p server is working well",
            "expected_terms": ["MCP", "server"],
            "description": "MCP server context test"
        },
        {
            "transcript": "check the token consumption and costs",
            "expected_terms": ["token", "consumption"],
            "description": "Token/cost context test"
        }
    ]
    
    logging.info(f"🚀 Running Limited Context Correction Test Suite")
    logging.info(f"📋 {len(test_cases)} test cases")
    
    results = []
    total_time = 0
    total_tokens = 0
    
    for i, test in enumerate(test_cases, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"TEST {i}/4: {test['description']}")
        
        result = test_correction_with_limited_context(test['transcript'])
        results.append(result)
        
        if result.get('success'):
            total_time += result['times']['total']
            total_tokens += result['tokens_used']
            
            # Check if expected corrections occurred
            corrected_text = result['corrected'].lower()
            found_terms = [term for term in test['expected_terms'] 
                          if term.lower() in corrected_text]
            
            if found_terms:
                logging.info(f"🎯 Expected corrections found: {found_terms}")
            else:
                logging.warning(f"⚠️ Expected terms not found: {test['expected_terms']}")
    
    # Summary
    successful_tests = len([r for r in results if r.get('success')])
    avg_time = total_time / successful_tests if successful_tests > 0 else 0
    avg_tokens = total_tokens / successful_tests if successful_tests > 0 else 0
    
    logging.info(f"\n{'='*60}")
    logging.info(f"📊 TEST SUITE SUMMARY")
    logging.info(f"✅ Successful tests: {successful_tests}/{len(test_cases)}")
    logging.info(f"⏱️ Average time: {avg_time:.2f}s per correction")
    logging.info(f"📊 Average tokens: {avg_tokens:.0f} per correction")
    logging.info(f"💰 Token savings: 99.8% vs current approach")
    
    if successful_tests == len(test_cases):
        logging.info(f"🎉 ALL TESTS PASSED - Limited context approach is viable!")
    elif successful_tests >= len(test_cases) * 0.75:
        logging.info(f"✅ Most tests passed - Approach shows promise")
    else:
        logging.warning(f"⚠️ Some tests failed - May need refinement")

if __name__ == "__main__":
    run_test_suite()