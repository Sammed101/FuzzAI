"""
Wordlist discovery and resolution utilities
"""

import os
from pathlib import Path
from typing import List, Dict
from utils.logger import get_logger

class WordlistResolver:
    """Find and categorize wordlists in configured directories"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger()
        self._wordlist_cache = None
    
    def find_all_wordlists(self, force_refresh=False) -> List[Dict]:
        """
        Find all wordlists in configured paths
        Returns list of dicts with path, name, category, size
        """
        if self._wordlist_cache and not force_refresh:
            return self._wordlist_cache
        
        wordlists = []
        search_paths = self.config.get_wordlist_paths()
        
        self.logger.debug(f"Searching for wordlists in {len(search_paths)} paths")
        
        for base_path in search_paths:
            if not os.path.isdir(base_path):
                continue
            
            self.logger.debug(f"Scanning: {base_path}")
            
            # Walk through directory tree
            for root, dirs, files in os.walk(base_path):
                for filename in files:
                    # Only consider text files
                    if not self._is_wordlist(filename):
                        continue
                    
                    filepath = os.path.join(root, filename)
                    
                    # Get file info
                    try:
                        size = os.path.getsize(filepath)
                        category = self._categorize_wordlist(filepath, filename)
                        
                        wordlists.append({
                            'path': filepath,
                            'filename': filename,
                            'category': category,
                            'size': size,
                            'relative_path': os.path.relpath(filepath, base_path)
                        })
                    except Exception as e:
                        self.logger.debug(f"Error processing {filepath}: {e}")
        
        self.logger.debug(f"Found {len(wordlists)} wordlists")
        self._wordlist_cache = wordlists
        return wordlists
    
    def _is_wordlist(self, filename: str) -> bool:
        """Check if file is likely a wordlist"""
        valid_extensions = ['.txt', '.list', '.dict', '.csv']
        
        # Check extension
        has_valid_ext = any(filename.endswith(ext) for ext in valid_extensions)
        
        # Or no extension (common for wordlists)
        no_ext = '.' not in filename
        
        # Exclude some common non-wordlist files
        exclude_patterns = ['.md', '.json', '.xml', '.html', 'readme', 'license']
        is_excluded = any(pattern in filename.lower() for pattern in exclude_patterns)
        
        return (has_valid_ext or no_ext) and not is_excluded
    
    def _categorize_wordlist(self, filepath: str, filename: str) -> str:
        """
        Categorize wordlist based on path and filename
        Categories: web, admin, api, directory, file, user, password, generic
        """
        path_lower = filepath.lower()
        name_lower = filename.lower()
        
        # Web content
        if any(x in path_lower for x in ['web-content', 'discovery', 'raft', 'dirbuster']):
            return 'web-content'
        
        # Admin/Management
        if any(x in name_lower for x in ['admin', 'panel', 'dashboard', 'manager']):
            return 'admin'
        
        # API endpoints
        if any(x in name_lower for x in ['api', 'endpoint', 'swagger', 'rest']):
            return 'api'
        
        # Directories
        if any(x in name_lower for x in ['directory', 'directories', 'dir', 'folder']):
            return 'directory'
        
        # Files/Extensions
        if any(x in name_lower for x in ['file', 'extension', 'ext', 'backup']):
            return 'file'
        
        # Usernames
        if any(x in name_lower for x in ['user', 'username', 'account', 'names']):
            return 'user'
        
        # Passwords
        if any(x in name_lower for x in ['password', 'pass', 'pwd']):
            return 'password'
        
        # Parameters
        if any(x in name_lower for x in ['parameter', 'param', 'params']):
            return 'parameter'
        
        # Common/Generic
        if any(x in name_lower for x in ['common', 'small', 'medium', 'big', 'large']):
            return 'generic'
        
        return 'other'
    
    def search_by_keywords(self, keywords: List[str], limit=10) -> List[Dict]:
        """
        Search wordlists by keywords
        Returns ranked list of matching wordlists
        """
        all_wordlists = self.find_all_wordlists()
        
        if not all_wordlists:
            return []
        
        scored_lists = []
        
        for wordlist in all_wordlists:
            score = self._score_wordlist(wordlist, keywords)
            if score > 0:
                scored_lists.append({
                    **wordlist,
                    'score': score
                })
        
        # Sort by score (descending) and size (ascending for equal scores)
        scored_lists.sort(key=lambda x: (-x['score'], x['size']))
        
        return scored_lists[:limit]
    
    def _score_wordlist(self, wordlist: Dict, keywords: List[str]) -> int:
        """
        Score wordlist based on keyword matches
        Higher score = better match
        """
        score = 0
        path = wordlist['path'].lower()
        filename = wordlist['filename'].lower()
        category = wordlist['category'].lower()
        
        for keyword in keywords:
            keyword = keyword.lower()
            
            # Exact match in filename (highest priority)
            if keyword in filename:
                score += 10
            
            # Match in path
            if keyword in path:
                score += 5
            
            # Match in category
            if keyword in category:
                score += 3
            
            # Fuzzy matches
            if self._fuzzy_match(keyword, filename):
                score += 2
        
        # Bonus for preferred categories
        if category in ['web-content', 'directory', 'generic']:
            score += 1
        
        # Penalty for very large files (might be slow)
        if wordlist['size'] > 10_000_000:  # > 10MB
            score -= 2
        
        return score
    
    def _fuzzy_match(self, keyword: str, text: str) -> bool:
        """Simple fuzzy matching"""
        # Remove common separators
        keyword_clean = keyword.replace('-', '').replace('_', '')
        text_clean = text.replace('-', '').replace('_', '')
        
        return keyword_clean in text_clean
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Get all wordlists of specific category"""
        all_wordlists = self.find_all_wordlists()
        return [w for w in all_wordlists if w['category'] == category]
    
    def get_popular_wordlists(self) -> List[str]:
        """Return paths to popular/recommended wordlists"""
        popular = [
            'common.txt',
            'directory-list-2.3-medium.txt',
            'raft-medium-directories.txt',
            'big.txt',
            'quick-common.txt'
        ]
        
        all_wordlists = self.find_all_wordlists()
        matches = []
        
        for wordlist in all_wordlists:
            if any(p in wordlist['filename'].lower() for p in popular):
                matches.append(wordlist['path'])
        
        return matches
