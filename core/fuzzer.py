"""
Main fuzzing engine with threading support
"""

import os
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
                 verbose: bool = False,
                 method: str = 'GET',
                 headers: Optional[dict] = None,
                 data: Optional[str] = None,
                 insecure: bool = False,
                 follow_redirects: bool = False,
                 proxy: Optional[str] = None,
                 explain: bool = False):
        
        self.url_template = url
        self.wordlist_path = wordlist_path
        self.threads = threads
        self.timeout = timeout
        self.delay = delay
        self.response_filter = response_filter
        self.output_file = output_file
        self.verbose = verbose
        self.method = method
        self.headers = headers or {}
        self.data = data
        self.insecure = insecure
        self.follow_redirects = follow_redirects
        self.proxy = proxy
        self.explain = explain
        
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
        
        # Check target reachability before starting
        url = self.url_template
        parsed = url.split('FUZZ')
        is_subdomain_mode = False
        if len(parsed) > 1:
            before = parsed[0]
            # If FUZZ is right after protocol (e.g., https://FUZZ.example.com/)
            if before.endswith('://') or before.endswith('://www.'):
                is_subdomain_mode = True
        if not is_subdomain_mode:
            self.logger.info(f"Target: {self.url_template}")
            self.logger.info("Checking target reachability...")
            if not self._check_target_reachability():
                self.logger.error("Target is not reachable or connection timed out.")
                self.logger.error(f"Please verify the target URL: {self.url_template}")
                return
            self.logger.success("✓ Target found and reachable")
        
        # Display wordlist info
        wordlist_basename = os.path.basename(self.wordlist_path)
        #self.logger.info(f"Selected wordlist: {wordlist_basename} ({self.total_requests} words)")
        if self.verbose:
            self.logger.debug(f"Full path: {self.wordlist_path}")
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
    
    def _check_target_reachability(self) -> bool:
        """Check if target is reachable by making a test request"""
        test_urls = []
        url = self.url_template
        # Detect fuzzing mode by FUZZ position
        parsed = url.split('FUZZ')
        if len(parsed) > 1:
            before = parsed[0]
            after = parsed[1]
            # If FUZZ is right after protocol (e.g., https://FUZZ.example.com/)
            if before.endswith('://') or before.endswith('://www.'):
                self.logger.info("Subdomain fuzzing detected")
                # Test base domain only
                base_url = before + after.lstrip('.')
                test_urls.append(base_url)
            else:
                self.logger.info("Path/parameter fuzzing detected")
                # Replace FUZZ with a known word
                test_urls.append(url.replace('FUZZ', 'test'))
                test_urls.append(url.replace('FUZZ', '123'))
                test_urls.append(url.replace('FUZZ', 'admin'))
        else:
            # No FUZZ found, fallback to original URL
            test_urls.append(url)

        # Try each test URL
        for test_url in test_urls:
            try:
                response = requests.head(
                    test_url,
                    timeout=self.timeout,
                    allow_redirects=False,
                    verify=False
                )
                # If we get any response (even 404), target is reachable
                self.logger.debug(f"Target reachability verified via: {test_url}")
                return True
            except requests.exceptions.Timeout:
                self.logger.debug(f"Target check timeout: {test_url}")
                continue
            except requests.exceptions.ConnectionError as e:
                self.logger.debug(f"Connection error to {test_url}: {e}")
                continue
            except requests.exceptions.RequestException as e:
                self.logger.debug(f"Request exception for {test_url}: {e}")
                continue
            except Exception as e:
                self.logger.debug(f"Unexpected error checking {test_url}: {e}")
                continue

        # If all test URLs failed, assume target might still be reachable
        # (network issues, DNS timeouts, etc. - be lenient)
        self.logger.debug("Could not verify target reachability, proceeding anyway (may timeout during fuzzing)")
        return True
    
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
            # Build request kwargs
            request_kwargs = {
                'timeout': self.timeout,
                'allow_redirects': self.follow_redirects,
                'verify': not self.insecure
            }
            
            # Add proxy if specified
            if self.proxy:
                request_kwargs['proxies'] = {'http': self.proxy, 'https': self.proxy}
            
            # Add headers
            headers = self.headers.copy() if self.headers else {}
            if headers:
                request_kwargs['headers'] = headers
            
            # Add data for POST requests
            if self.data:
                data = self.data.replace('FUZZ', word)
                request_kwargs['data'] = data
            
            # Make request
            start = time.time()
            if self.method.upper() == 'GET':
                response = requests.get(url, **request_kwargs)
            elif self.method.upper() == 'POST':
                response = requests.post(url, **request_kwargs)
            elif self.method.upper() == 'HEAD':
                response = requests.head(url, **request_kwargs)
            elif self.method.upper() == 'PUT':
                response = requests.put(url, **request_kwargs)
            elif self.method.upper() == 'DELETE':
                response = requests.delete(url, **request_kwargs)
            elif self.method.upper() == 'PATCH':
                response = requests.patch(url, **request_kwargs)
            else:
                response = requests.request(self.method, url, **request_kwargs)
            
            elapsed = time.time() - start
            
            # Extract response metadata
            status_code = response.status_code
            content = response.text
            size = len(response.content)
            lines = content.count('\n')
            words = len(content.split())
            
            # Check filters
            should_display = True
            filter_reason = None
            if self.response_filter:
                should_display = self.response_filter.should_display(
                    status_code, size, lines, words
                )
                if not should_display:
                    # Determine why it was filtered
                    if status_code in self.response_filter.filter_codes:
                        filter_reason = f"status code {status_code} is filtered"
                    elif size in self.response_filter.filter_sizes:
                        filter_reason = f"size {size} is filtered"
                    elif lines in self.response_filter.filter_lines:
                        filter_reason = f"lines {lines} is filtered"
                    elif words in self.response_filter.filter_words:
                        filter_reason = f"words {words} is filtered"
            
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
                    
                if self.verbose and filter_reason:
                    self.logger.debug(f"Filtered ({filter_reason}): {status_code} {url} [size={size}, words={words}, lines={lines}]")
        
        except requests.exceptions.Timeout:
            if self.verbose:
                self.logger.debug(f"Timeout: {url}")
        
        except requests.exceptions.RequestException as e:
            if self.verbose:
                self.logger.debug(f"Request Failed: {url:35} : {type(e).__name__}")

        
        except Exception as e:
            self.logger.debug(f"Unexpected error: {url:50} : {type(e).__name__}")

