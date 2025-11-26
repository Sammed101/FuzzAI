"""
Main fuzzing engine with threading support
"""

import time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from threading import Thread, Lock
from queue import Queue
from typing import Optional
from urllib.parse import urlparse
from utils.logger import get_logger

class FuzzResult:
    """Store fuzzing result"""
    def __init__(self, url, status_code, size, words, lines, elapsed):
        self.url = url
        self.status_code = status_code
        self.size = size
        self.words = words
        self.lines = lines
        self.elapsed = elapsed

class Fuzzer:
    
    """Main fuzzing engine"""
    
    def __init__(self, 
                 url: str,
                 wordlist_path: str,
                 threads: int = 10,
                 timeout: int = 10,
                 delay: float = 0,
                 response_filter = None,
                 output_file: Optional[str] = None,
                 verbose: bool = False):
        
        self.url_template = url
        self.wordlist_path = wordlist_path
        self.threads = threads
        self.timeout = timeout
        self.delay = delay
        self.response_filter = response_filter
        self.output_file = output_file
        self.verbose = verbose
        
        self.logger = get_logger()
        
        # Statistics
        self.total_requests = 0
        self.found_count = 0
        self.filtered_count = 0
        self.start_time = None
        
        # Thread-safe structures
        self.queue = Queue()
        self.results_lock = Lock()
        self.results = []
        
        # Output file handle
        self.output_handle = None
    
    def run(self):
        """Execute fuzzing"""
        # Load wordlist
        words = self._load_wordlist()
        if not words:
            self.logger.error("Empty wordlist")
            return
        
        self.total_requests = len(words)
        self.logger.info(f"Target: {self.url_template}")
        self.logger.info(f"Wordlist: {self.wordlist_path} ({self.total_requests} words)")
        self.logger.info(f"Threads: {self.threads}")
        
        if self.response_filter and self.response_filter.has_filters():
            self.logger.info(f"Filters: {self.response_filter.get_summary()}")
        
        # Open output file if specified
        if self.output_file:
            self.output_handle = open(self.output_file, 'w')
            self.logger.info(f"Saving results to: {self.output_file}")
        
        self.logger.info("\nStarting fuzzing...\n")
        
        # Add words to queue
        for word in words:
            self.queue.put(word)
        
        # Start timing
        self.start_time = time.time()
        
        # Start worker threads
        threads = []
        for i in range(self.threads):
            t = Thread(target=self._worker, daemon=True)
            t.start()
            threads.append(t)
        
        # Wait for completion
        self.queue.join()
        
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        
        # Close output file
        if self.output_handle:
            self.output_handle.close()
        
        # Print statistics
        self.logger.stats(
            total=self.total_requests,
            found=self.found_count,
            filtered=self.filtered_count,
            elapsed=elapsed
        )
        
        if self.output_file:
            self.logger.success(f"Results saved to: {self.output_file}")
    
    def _load_wordlist(self) -> list:
        """Load words from wordlist file"""
        try:
            with open(self.wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                words = [line.strip() for line in f if line.strip()]
            return words
        except Exception as e:
            self.logger.error(f"Failed to load wordlist: {e}")
            return []
    
    def _worker(self):
        """Worker thread for fuzzing"""
        while True:
            try:
                word = self.queue.get(timeout=1)
            except:
                break
            
            try:
                self._fuzz_word(word)
            except Exception as e:
                self.logger.debug(f"Error fuzzing '{word}': {e}")
            finally:
                self.queue.task_done()
                
                # Apply delay if specified
                if self.delay > 0:
                    time.sleep(self.delay)
    
    def _fuzz_word(self, word: str):
        """Fuzz single word"""
        # Build URL
        url = self.url_template.replace('FUZZ', word)
        
        try:
            # Make request
            start = time.time()
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=False,
                verify=False  # Skip SSL verification for testing
            )
            elapsed = time.time() - start
            
            # Extract response metadata
            status_code = response.status_code
            content = response.text
            size = len(response.content)
            lines = content.count('\n')
            words = len(content.split())
            
            # Check filters
            should_display = True
            if self.response_filter:
                should_display = self.response_filter.should_display(
                    status_code, size, lines, words
                )
            
            if should_display:
                # Display result
                with self.results_lock:
                    self.found_count += 1
                    self.logger.result(status_code, url, size, words, lines)
                    
                    # Save to file
                    if self.output_handle:
                        self.output_handle.write(
                            f"{status_code}\t{url}\t{size}\t{words}\t{lines}\n"
                        )
                        self.output_handle.flush()
                    
                    # Store result
                    result = FuzzResult(url, status_code, size, words, lines, elapsed)
                    self.results.append(result)
            else:
                with self.results_lock:
                    self.filtered_count += 1
                    
                if self.verbose:
                    self.logger.debug(f"Filtered: {status_code} {url}")
        
        except requests.exceptions.Timeout:
            if self.verbose:
                self.logger.debug(f"Timeout: {url}")
        
        except requests.exceptions.RequestException as e:
            if self.verbose:
                self.logger.debug(f"Request failed: {url} - {e}")
        
        except Exception as e:
            self.logger.debug(f"Unexpected error for {url}: {e}")
