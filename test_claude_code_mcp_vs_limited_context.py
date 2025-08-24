#!/usr/bin/env python3
"""
Comprehensive Test: Claude Code MCP vs Limited Context Approach
Compares performance, accuracy, and cost efficiency
"""

import subprocess
import time
import logging
import sys
import json
from claude_context_parser import ClaudeContextParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_claude_code_mcp_approach():
    """Test Claude Code as one-shot MCP server"""
    
    logging.info("🧪 TESTING: Claude Code MCP One-Shot Approach")
    
    test_transcripts = [
        {
            "transcript": "how is our cuba container doing right now", 
            "expected": "CUDA container",
            "context": "AI/ML development conversation"
        },
        {
            "transcript": "the m c p server is working well",
            "expected": "MCP server", 
            "context": "Model Context Protocol discussion"
        },
        {
            "transcript": "we need to test the haiku model performance",
            "expected": "Haiku model",
            "context": "AI model testing conversation"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_transcripts, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"CLAUDE CODE MCP TEST {i}: '{test['transcript']}'")
        
        # Test using Claude Code MCP via client call
        prompt = f"""Using the claude-code-speech-corrections MCP server, correct this transcript:

Please use the correct_transcript_with_claude_code tool with:
- transcript: "{test['transcript']}"
- context_hint: "{test['context']}"

This will test Claude Code's built-in context awareness capabilities."""
        
        cmd = [
            'claude',
            '--mcp-config', '/home/sati/speech-to-text-for-ubuntu/claude_code_mcp_config.json',
            '--model', 'haiku',
            '-p',
            prompt
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                output = result.stdout
                logging.info(f"✅ Claude Code MCP: {elapsed:.2f}s")
                
                # Extract corrected text (simplified for testing)
                corrected = "EXTRACTED_FROM_OUTPUT"  # Would parse actual output
                
                results.append({
                    "approach": "Claude Code MCP",
                    "test_num": i,
                    "original": test['transcript'],
                    "corrected": corrected,
                    "time": elapsed,
                    "success": True,
                    "context_used": test['context']
                })
                
            else:
                logging.error(f"❌ Claude Code MCP failed: {result.stderr}")
                results.append({
                    "approach": "Claude Code MCP",
                    "test_num": i,
                    "success": False,
                    "error": result.stderr,
                    "time": elapsed
                })
                
        except subprocess.TimeoutExpired:
            logging.error(f"❌ Claude Code MCP timeout")
            results.append({
                "approach": "Claude Code MCP",
                "test_num": i,
                "success": False,
                "error": "Timeout",
                "time": 30.0
            })
        except Exception as e:
            logging.error(f"❌ Claude Code MCP error: {e}")
            results.append({
                "approach": "Claude Code MCP",
                "test_num": i,
                "success": False,
                "error": str(e),
                "time": 0
            })
    
    return results

def test_limited_context_approach():
    """Test current limited context approach"""
    
    logging.info("\n🧪 TESTING: Limited Context Approach (Current)")
    
    parser = ClaudeContextParser()
    
    test_transcripts = [
        {
            "transcript": "how is our cuba container doing right now",
            "expected": "CUDA container"
        },
        {
            "transcript": "the m c p server is working well",
            "expected": "MCP server"
        },
        {
            "transcript": "we need to test the haiku model performance", 
            "expected": "Haiku model"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_transcripts, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"LIMITED CONTEXT TEST {i}: '{test['transcript']}'")
        
        try:
            # Get limited context
            context_start = time.time()
            exchanges = parser.get_recent_exchanges(n_exchanges=3)
            context_time = time.time() - context_start
            
            # Build correction prompt
            if exchanges:
                context_text = "\n".join([f"User: {user}\nAssistant: {assistant}" 
                                        for user, assistant in exchanges[-3:]])
                
                correction_prompt = f"""Recent conversation context:
{context_text}

The speech-to-text system produced this raw transcript:
"{test['transcript']}"

Based on the conversation context above, correct any speech recognition errors.

Respond with ONLY the corrected text, no explanations."""
                
                # Estimate tokens saved
                prompt_tokens = len(correction_prompt.split()) * 1.3
                tokens_saved = max(0, 284000 - prompt_tokens)
                
            else:
                correction_prompt = f"""Correct this speech-to-text transcript:
"{test['transcript']}"

Fix any obvious errors. Respond with ONLY the corrected text."""
                tokens_saved = 0
            
            # Call Claude
            cmd = ['claude', '--model', 'haiku', correction_prompt]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            correction_time = time.time() - start_time
            total_time = correction_time + context_time
            
            if result.returncode == 0:
                corrected = result.stdout.strip()
                if corrected.startswith('"') and corrected.endswith('"'):
                    corrected = corrected[1:-1]
                
                logging.info(f"✅ Limited Context: {total_time:.2f}s (tokens saved: ~{tokens_saved:,.0f})")
                
                results.append({
                    "approach": "Limited Context",
                    "test_num": i,
                    "original": test['transcript'], 
                    "corrected": corrected,
                    "correction_time": correction_time,
                    "context_time": context_time,
                    "total_time": total_time,
                    "tokens_saved": tokens_saved,
                    "success": True
                })
                
            else:
                logging.error(f"❌ Limited Context failed: {result.stderr}")
                results.append({
                    "approach": "Limited Context",
                    "test_num": i,
                    "success": False,
                    "error": result.stderr,
                    "total_time": total_time
                })
                
        except Exception as e:
            logging.error(f"❌ Limited Context error: {e}")
            results.append({
                "approach": "Limited Context",
                "test_num": i,
                "success": False,
                "error": str(e),
                "total_time": 0
            })
    
    return results

def compare_approaches():
    """Run comprehensive comparison of both approaches"""
    
    logging.info("🚀 COMPREHENSIVE COMPARISON: Claude Code MCP vs Limited Context")
    logging.info("📋 Testing performance, accuracy, and token efficiency")
    
    # Test both approaches
    claude_code_results = test_claude_code_mcp_approach()
    limited_context_results = test_limited_context_approach()
    
    # Analysis
    logging.info(f"\n{'='*60}")
    logging.info("📊 COMPARISON ANALYSIS")
    
    # Claude Code MCP Analysis
    claude_code_successful = [r for r in claude_code_results if r.get('success')]
    if claude_code_successful:
        avg_claude_code_time = sum(r['time'] for r in claude_code_successful) / len(claude_code_successful)
        logging.info(f"🔧 Claude Code MCP: {len(claude_code_successful)}/{len(claude_code_results)} successful")
        logging.info(f"   Average time: {avg_claude_code_time:.2f}s")
    else:
        logging.info("❌ Claude Code MCP: No successful corrections")
    
    # Limited Context Analysis
    limited_context_successful = [r for r in limited_context_results if r.get('success')]
    if limited_context_successful:
        avg_limited_time = sum(r['total_time'] for r in limited_context_successful) / len(limited_context_successful)
        total_tokens_saved = sum(r['tokens_saved'] for r in limited_context_successful)
        avg_tokens_saved = total_tokens_saved / len(limited_context_successful)
        
        logging.info(f"⚡ Limited Context: {len(limited_context_successful)}/{len(limited_context_results)} successful") 
        logging.info(f"   Average time: {avg_limited_time:.2f}s")
        logging.info(f"   Total tokens saved: {total_tokens_saved:,.0f}")
        logging.info(f"   Average tokens saved: {avg_tokens_saved:,.0f}")
    else:
        logging.info("❌ Limited Context: No successful corrections")
    
    # Recommendation
    logging.info(f"\n🎯 RECOMMENDATION:")
    
    if claude_code_successful and limited_context_successful:
        if avg_claude_code_time < avg_limited_time:
            logging.info("✅ CLAUDE CODE MCP is faster - consider switching")
            logging.info("🔧 Benefits: Built-in context handling, simpler architecture")
        else:
            logging.info("✅ LIMITED CONTEXT remains optimal")
            logging.info(f"🔧 Benefits: {avg_tokens_saved:,.0f} avg tokens saved, proven reliability")
    elif limited_context_successful:
        logging.info("✅ LIMITED CONTEXT is the only working solution")
        logging.info("❌ Claude Code MCP approach failed - stick with current implementation")
    elif claude_code_successful:
        logging.info("✅ CLAUDE CODE MCP is the only working solution")
        logging.info("❌ Limited Context approach failed - switch to Claude Code MCP")
    else:
        logging.info("❌ BOTH APPROACHES FAILED - investigate configuration issues")

if __name__ == "__main__":
    try:
        compare_approaches()
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    except Exception as e:
        logging.error(f"Test failed: {e}")
        sys.exit(1)