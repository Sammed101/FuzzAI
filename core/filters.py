"""
Response filtering and matching logic (like ffuf)
"""

from typing import Optional, Set
from utils.logger import get_logger

class ResponseFilter:
    """Filter responses based on various criteria"""
    
    def __init__(self,
                 filter_codes: Optional[str] = None,
                 filter_sizes: Optional[str] = None,
                 filter_lines: Optional[str] = None,
                 filter_words: Optional[str] = None,
                 match_codes: Optional[str] = None,
                 match_sizes: Optional[str] = None,
                 match_lines: Optional[str] = None,
                 match_words: Optional[str] = None):
        
        self.logger = get_logger()
        
        # Parse filter criteria (exclude)
        self.filter_codes = self._parse_csv(filter_codes, int) if filter_codes else set()
        self.filter_sizes = self._parse_csv(filter_sizes, int) if filter_sizes else set()
        self.filter_lines = self._parse_csv(filter_lines, int) if filter_lines else set()
        self.filter_words = self._parse_csv(filter_words, int) if filter_words else set()
        
        # Parse match criteria (include only)
        self.match_codes = self._parse_csv(match_codes, int) if match_codes else set()
        self.match_sizes = self._parse_csv(match_sizes, int) if match_sizes else set()
        self.match_lines = self._parse_csv(match_lines, int) if match_lines else set()
        self.match_words = self._parse_csv(match_words, int) if match_words else set()
        
        self._log_filters()
    
    def _parse_csv(self, csv_string: str, dtype=int) -> Set:
        """Parse comma-separated values into set"""
        try:
            return {dtype(x.strip()) for x in csv_string.split(',') if x.strip()}
        except ValueError as e:
            self.logger.error(f"Invalid filter value: {csv_string}")
            return set()
    
    def _log_filters(self):
        """Log active filters"""
        if self.filter_codes:
            self.logger.debug(f"Filter codes: {self.filter_codes}")
        if self.filter_sizes:
            self.logger.debug(f"Filter sizes: {self.filter_sizes}")
        if self.filter_lines:
            self.logger.debug(f"Filter lines: {self.filter_lines}")
        if self.filter_words:
            self.logger.debug(f"Filter words: {self.filter_words}")
        
        if self.match_codes:
            self.logger.debug(f"Match codes: {self.match_codes}")
        if self.match_sizes:
            self.logger.debug(f"Match sizes: {self.match_sizes}")
        if self.match_lines:
            self.logger.debug(f"Match lines: {self.match_lines}")
        if self.match_words:
            self.logger.debug(f"Match words: {self.match_words}")
    
    def should_display(self, status_code: int, size: int, lines: int, words: int) -> bool:
        """
        Determine if response should be displayed
        Returns True if response passes all filters
        """
        # First, check match criteria (whitelist)
        # If any match criteria are set, response must match at least one
        if self.match_codes or self.match_sizes or self.match_lines or self.match_words:
            matches = []
            
            if self.match_codes:
                matches.append(status_code in self.match_codes)
            if self.match_sizes:
                matches.append(size in self.match_sizes)
            if self.match_lines:
                matches.append(lines in self.match_lines)
            if self.match_words:
                matches.append(words in self.match_words)
            
            # Must match at least one criterion
            if not any(matches):
                return False
        
        # Then, check filter criteria (blacklist)
        # If response matches any filter, exclude it
        if status_code in self.filter_codes:
            return False
        
        if size in self.filter_sizes:
            return False
        
        if lines in self.filter_lines:
            return False
        
        if words in self.filter_words:
            return False
        
        return True
    
    def has_filters(self) -> bool:
        """Check if any filters are active"""
        return bool(
            self.filter_codes or self.filter_sizes or 
            self.filter_lines or self.filter_words or
            self.match_codes or self.match_sizes or 
            self.match_lines or self.match_words
        )
    
    def get_summary(self) -> str:
        """Get human-readable summary of active filters"""
        parts = []
        
        if self.filter_codes:
            parts.append(f"Filtering codes: {', '.join(map(str, sorted(self.filter_codes)))}")
        if self.filter_sizes:
            parts.append(f"Filtering sizes: {', '.join(map(str, sorted(self.filter_sizes)))}")
        if self.filter_lines:
            parts.append(f"Filtering lines: {', '.join(map(str, sorted(self.filter_lines)))}")
        if self.filter_words:
            parts.append(f"Filtering words: {', '.join(map(str, sorted(self.filter_words)))}")
        
        if self.match_codes:
            parts.append(f"Matching codes: {', '.join(map(str, sorted(self.match_codes)))}")
        if self.match_sizes:
            parts.append(f"Matching sizes: {', '.join(map(str, sorted(self.match_sizes)))}")
        if self.match_lines:
            parts.append(f"Matching lines: {', '.join(map(str, sorted(self.match_lines)))}")
        if self.match_words:
            parts.append(f"Matching words: {', '.join(map(str, sorted(self.match_words)))}")
        
        return " | ".join(parts) if parts else "No filters active"
