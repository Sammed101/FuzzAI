"""
Configuration management for FuzzAI
"""

import json
import os
from pathlib import Path

class Config:
    """Manage FuzzAI configuration"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.fuzzai'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'wordlist_paths': [],
                'seclists_path': None,
                'openai_key': None
            }
            self._save_config()
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get_wordlist_paths(self):
        """Get all configured wordlist paths"""
        paths = [
            './wordlists/',
            '/usr/share/seclists/',
            '/usr/share/wordlists/',
        ]
        
        # Add SecLists path if configured
        if self.data.get('seclists_path'):
            paths.append(self.data['seclists_path'])
        
        # Add custom paths
        paths.extend(self.data.get('wordlist_paths', []))
        
        return [p for p in paths if os.path.isdir(p)]
    
    def set_seclists_path(self, path):
        """Configure SecLists installation path (normalize and persist)"""
        import os
        if path is None:
            self.data['seclists_path'] = None
            self._save_config()
            return True

        # expand ~ and normalize
        p = os.path.abspath(os.path.expanduser(str(path)))

        if not os.path.isdir(p):
            # Provide a clearer error message
            raise ValueError(f"Path does not exist or is not a directory: {p}")

        self.data['seclists_path'] = str(p)
        self._save_config()
        return True
   
    def get_seclists_path(self):
        """Return the configured SecLists path (normalized) or None"""
        p = self.data.get('seclists_path')
        if not p:
            return None
        return os.path.abspath(os.path.expanduser(str(p)))

    
    def add_wordlist_path(self, path):
        """Add custom wordlist directory"""
        if not os.path.isdir(path):
            raise ValueError(f"Path does not exist: {path}")
        
        if 'wordlist_paths' not in self.data:
            self.data['wordlist_paths'] = []
        
        if path not in self.data['wordlist_paths']:
            self.data['wordlist_paths'].append(str(path))
            self._save_config()
    
    def get_openai_key(self):
        """Get OpenAI API key"""
        # Check environment variable first
        env_key = os.getenv('OPENAI_API_KEY')
        if env_key:
            return env_key
        
        return self.data.get('openai_key')
    
    def set_openai_key(self, key):
        """Set OpenAI API key"""
        self.data['openai_key'] = key
        self._save_config()
