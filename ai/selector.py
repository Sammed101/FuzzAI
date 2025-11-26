"""
AI-powered wordlist selection based on user prompt
"""

import re
from typing import Optional, List
from utils.logger import get_logger

class AIWordlistSelector:
    """Select best wordlist based on user prompt"""
    
    def __init__(self, wordlist_resolver):
        self.resolver = wordlist_resolver
        self.logger = get_logger()
        
        # Keyword mappings for common fuzzing scenarios
        self.intent_keywords = {
            'admin': ['admin', 'panel', 'dashboard', 'manager', 'control'],
            'api': ['api', 'endpoint', 'rest', 'swagger', 'graphql'],
            'directory': ['directory', 'folder', 'dir', 'path'],
            'file': ['file', 'backup', 'config', 'document', 'upload'],
            'user': ['user', 'username', 'account', 'profile'],
            'auth': ['login', 'auth', 'signin', 'register', 'password'],
            'generic': ['common', 'general', 'basic', 'quick'],
            'web': ['web', 'page', 'content', 'site'],
        }
    
    def select_wordlist(self, prompt: str) -> Optional[str]:
        """
        Select best wordlist based on user prompt
        Returns path to selected wordlist or None
        """
        self.logger.debug(f"Processing prompt: '{prompt}'")
        
        # Extract keywords from prompt
        keywords = self._extract_keywords(prompt)
        self.logger.debug(f"Extracted keywords: {keywords}")
        
        # Search for matching wordlists
        candidates = self.resolver.search_by_keywords(keywords, limit=5)
        
        if not candidates:
            self.logger.warning("No matching wordlists found")
            return None
        
        # Select best candidate
        best_match = self._select_best(candidates, prompt)
        
        if best_match:
            self.logger.debug(f"Best match: {best_match['filename']} (score: {best_match['score']})")
            return best_match['path']
        
        return None
    
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract meaningful keywords from user prompt"""
        prompt_lower = prompt.lower()
        keywords = []
        
        # Check for intent matches
        for intent, intent_keywords in self.intent_keywords.items():
            for keyword in intent_keywords:
                if keyword in prompt_lower:
                    keywords.extend(intent_keywords)
                    break
        
        # Extract individual words (3+ chars)
        words = re.findall(r'\b\w{3,}\b', prompt_lower)
        keywords.extend(words)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)
        
        return unique_keywords
    
    def _select_best(self, candidates: List[dict], prompt: str) -> Optional[dict]:
        """
        Select best wordlist from candidates
        Apply additional heuristics
        """
        if not candidates:
            return None
        
        # If only one candidate, return it
        if len(candidates) == 1:
            return candidates[0]
        
        # Apply size preferences
        prompt_lower = prompt.lower()
        
        # Prefer smaller lists for "quick", "small", "fast"
        if any(word in prompt_lower for word in ['quick', 'small', 'fast', 'short']):
            candidates.sort(key=lambda x: x['size'])
        
        # Prefer larger lists for "comprehensive", "thorough", "large", "big"
        elif any(word in prompt_lower for word in ['comprehensive', 'thorough', 'large', 'big', 'extensive']):
            candidates.sort(key=lambda x: -x['size'])
        
        # Prefer medium-sized lists for "medium", "moderate"
        elif any(word in prompt_lower for word in ['medium', 'moderate']):
            # Find closest to 100KB-1MB range
            target_size = 500_000  # 500KB
            candidates.sort(key=lambda x: abs(x['size'] - target_size))
        
        # Return top candidate
        return candidates[0]
    
    def explain_selection(self, wordlist_path: str, prompt: str) -> str:
        """Generate explanation for wordlist selection"""
        all_wordlists = self.resolver.find_all_wordlists()
        wordlist = next((w for w in all_wordlists if w['path'] == wordlist_path), None)
        
        if not wordlist:
            return "Unknown wordlist"
        
        size_mb = wordlist['size'] / (1024 * 1024)
        
        explanation = f"""
Selected: {wordlist['filename']}
Category: {wordlist['category']}
Size: {size_mb:.2f} MB
Path: {wordlist['relative_path']}

This wordlist was chosen based on keyword matching with your prompt: "{prompt}"
"""
        return explanation
