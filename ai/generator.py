"""
GPT-powered custom wordlist generation
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

class GPTWordlistGenerator:
    """Generate custom wordlists using OpenAI GPT"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = get_logger()
        self.output_dir = Path('./wordlists/generated')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, prompt: str) -> Optional[str]:
        """
        Generate wordlist based on prompt
        Returns path to generated wordlist file
        """
        try:
            self.logger.info("Contacting OpenAI API...")
            
            # Prepare system prompt
            system_prompt = self._build_system_prompt()
            
            # Call OpenAI API
            wordlist_content = self._call_gpt(system_prompt, prompt)
            
            if not wordlist_content:
                self.logger.error("GPT returned empty response")
                return None
            
            # Parse and clean wordlist
            wordlist_lines = self._parse_wordlist(wordlist_content)
            
            if not wordlist_lines:
                self.logger.error("No valid words generated")
                return None
            
            # Save to file
            output_path = self._save_wordlist(wordlist_lines, prompt)
            
            self.logger.info(f"Generated {len(wordlist_lines)} entries")
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate wordlist: {str(e)}")
            return None
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for GPT"""
        return """You are a wordlist generator for web application fuzzing and penetration testing.

Your task is to generate wordlists based on user requests. Follow these rules:

1. Generate ONE WORD PER LINE
2. No explanations, no markdown, no code blocks
3. No numbering or bullets
4. Just the raw wordlist content
5. Be comprehensive and relevant to the request
6. Include variations (case, separators like -, _, .)
7. For numeric ranges, include all numbers
8. For common patterns, include typical variations

Example request: "admin pages"
Expected output:
admin
administrator
admin-panel
admin_panel
adminpanel
dashboard
control-panel
management
...

Example request: "numbers 1-50"
Expected output:
1
2
3
...
50

Be creative and thorough while staying relevant to the user's request."""
    
    def _call_gpt(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API"""
        import requests
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        return content.strip()
    
    def _parse_wordlist(self, content: str) -> list:
        """Parse and clean GPT output into wordlist"""
        lines = content.split('\n')
        cleaned = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip markdown code blocks
            if line.startswith('```'):
                continue
            
            # Remove common prefixes (bullets, numbers)
            line = line.lstrip('-*•').strip()
            line = line.split('.', 1)[-1].strip() if line and line[0].isdigit() else line
            
            # Skip lines that look like explanations
            if len(line) > 100 or ' ' in line and len(line.split()) > 3:
                continue
            
            # Clean the word
            word = line.strip().replace('"', '').replace("'", '')
            
            if word and len(word) <= 100:
                cleaned.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for word in cleaned:
            if word.lower() not in seen:
                seen.add(word.lower())
                unique.append(word)
        
        return unique
    
    def _save_wordlist(self, wordlist: list, prompt: str) -> str:
        """Save wordlist to file"""
        # Generate filename from prompt
        safe_prompt = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_prompt}_{timestamp}.txt"
        
        output_path = self.output_dir / filename
        
        # Write wordlist
        with open(output_path, 'w') as f:
            for word in wordlist:
                f.write(f"{word}\n")
        
        # Also save metadata
        metadata = {
            'prompt': prompt,
            'generated_at': datetime.now().isoformat(),
            'count': len(wordlist),
            'filename': filename
        }
        
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(output_path)
