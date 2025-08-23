#!/usr/bin/env python3
"""
Claude Code Context Parser
Extracts recent conversation exchanges for limited context transcript correction
"""

import json
import glob
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

class ClaudeContextParser:
    """Parse Claude Code conversation history for context extraction"""
    
    def __init__(self, project_path: str = None):
        """Initialize parser with project path"""
        if project_path is None:
            # Auto-detect current project based on working directory
            cwd = os.getcwd()
            project_name = cwd.replace('/', '-')
            self.project_path = f"/home/sati/.claude/projects/{project_name}"
        else:
            self.project_path = project_path
    
    def find_current_conversation(self) -> Optional[str]:
        """Find the most recent conversation file"""
        try:
            conversation_files = glob.glob(f"{self.project_path}/*.jsonl")
            if not conversation_files:
                logging.warning(f"No conversation files found in {self.project_path}")
                return None
            
            # Get the most recent file by modification time
            latest_file = max(conversation_files, key=os.path.getmtime)
            logging.info(f"Found current conversation: {latest_file}")
            return latest_file
            
        except Exception as e:
            logging.error(f"Error finding conversation: {e}")
            return None
    
    def parse_conversation_file(self, file_path: str) -> List[Dict]:
        """Parse JSONL conversation file into structured messages"""
        messages = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('type') in ['user', 'assistant']:
                            messages.append(entry)
                    except json.JSONDecodeError:
                        continue  # Skip malformed lines
                        
        except Exception as e:
            logging.error(f"Error parsing conversation file: {e}")
            
        return messages
    
    def extract_text_content(self, message_entry: Dict) -> str:
        """Extract readable text from message content"""
        try:
            content = message_entry.get('message', {}).get('content', [])
            
            text_parts = []
            for item in content:
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'tool_use':
                    # Include tool use info for context
                    tool_name = item.get('name', 'unknown')
                    text_parts.append(f"[Used tool: {tool_name}]")
            
            return ' '.join(text_parts).strip()
            
        except Exception:
            return ""
    
    def get_recent_exchanges(self, n_exchanges: int = 3) -> List[Tuple[str, str]]:
        """
        Get the last N conversation exchanges (user-assistant pairs)
        Returns list of (user_message, assistant_message) tuples
        """
        conversation_file = self.find_current_conversation()
        if not conversation_file:
            return []
        
        messages = self.parse_conversation_file(conversation_file)
        if not messages:
            return []
        
        # Group messages into exchanges
        exchanges = []
        current_user_msg = None
        
        for msg in messages:
            msg_type = msg.get('type')
            text = self.extract_text_content(msg)
            
            if not text or len(text) < 10:  # Skip very short messages
                continue
                
            if msg_type == 'user':
                current_user_msg = text
            elif msg_type == 'assistant' and current_user_msg:
                exchanges.append((current_user_msg, text))
                current_user_msg = None
        
        # Return last N exchanges
        return exchanges[-n_exchanges:]
    
    def format_context_for_correction(self, exchanges: List[Tuple[str, str]]) -> str:
        """Format recent exchanges for transcript correction context"""
        if not exchanges:
            return "No recent conversation context available."
        
        context_parts = ["Recent conversation context:"]
        
        for i, (user_msg, assistant_msg) in enumerate(exchanges, 1):
            # Truncate very long messages
            user_short = user_msg[:200] + "..." if len(user_msg) > 200 else user_msg
            assistant_short = assistant_msg[:200] + "..." if len(assistant_msg) > 200 else assistant_msg
            
            context_parts.append(f"\n{i}. User: {user_short}")
            context_parts.append(f"   Assistant: {assistant_short}")
        
        return '\n'.join(context_parts)
    
    def get_context_for_transcript_correction(self, n_exchanges: int = 3) -> str:
        """
        Get formatted context for transcript correction
        Main method to be used by MCP server
        """
        exchanges = self.get_recent_exchanges(n_exchanges)
        return self.format_context_for_correction(exchanges)

def test_context_parser():
    """Test the context parser"""
    parser = ClaudeContextParser()
    
    print("=== Testing Context Parser ===")
    
    # Test finding conversation
    conv_file = parser.find_current_conversation()
    print(f"Current conversation: {conv_file}")
    
    # Test extracting recent exchanges
    exchanges = parser.get_recent_exchanges(3)
    print(f"\nFound {len(exchanges)} recent exchanges")
    
    # Test formatted context
    context = parser.get_context_for_transcript_correction(3)
    print(f"\n=== Formatted Context ===")
    print(context)
    
    return context

if __name__ == "__main__":
    test_context_parser()