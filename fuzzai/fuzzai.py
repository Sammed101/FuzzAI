import argparse
import threading
from queue import Queue
from utils.http_client import make_request
from utils.wordlist_loader import load_wordlist

# Worker function for threading
def worker(url_template, queue):
    while True:
        word = queue.get()
        if word is None:
            break
        # Replace FUZZ in the URL with the current word
        url = url_template.replace('FUZZ', word)
        status_code, response_length = make_request(url)
        print(f"{word:20} | Status: {status_code} | Size: {response_length}")
        queue.task_done()

# Main function to parse arguments and start fuzzing
def main():
    parser = argparse.ArgumentParser(description="FuzzAI: Simple CLI Fuzzer")
    parser.add_argument('-u', '--url', required=True, help='Target URL with FUZZ keyword')
    parser.add_argument('-w', '--wordlist', required=True, help='Path to wordlist file')
    parser.add_argument('-t', '--threads', type=int, default=10, help='Number of threads (default: 10)')
    args = parser.parse_args()

    # Load wordlist
    try:
        words = load_wordlist(args.wordlist)
    except Exception as e:
        print(f"Error loading wordlist: {e}")
        return

    # Check FUZZ keyword in URL
    if 'FUZZ' not in args.url:
        print("Error: URL must contain the 'FUZZ' keyword.")
        return

    # Create a queue and add all words
    queue = Queue()
    for word in words:
        queue.put(word)

    # Start worker threads
    threads = []
    for _ in range(args.threads):
        t = threading.Thread(target=worker, args=(args.url, queue))
        t.daemon = True
        t.start()
        threads.append(t)

    # Wait for all tasks to finish
    queue.join()

    # Stop workers
    for _ in range(args.threads):
        queue.put(None)
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
