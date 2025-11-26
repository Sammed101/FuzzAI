# FuzzAI

A simple Python CLI fuzzing tool inspired by ffuf.

## Features
- Fuzzes URLs by replacing the `FUZZ` keyword with words from a wordlist
- Displays status code and response size for each request
- Multithreaded for speed

## Usage

1. Place your wordlist in the `wordlists/` directory (e.g., `wordlists/common.txt`).
2. Run the tool:

```
python fuzzai.py -u "https://example.com/FUZZ" -w wordlists/common.txt
```

Optional arguments:
- `-t`, `--threads` : Number of threads (default: 10)

## Example

```
python fuzzai.py -u "https://example.com/FUZZ" -w wordlists/common.txt -t 20
```

## Requirements
- Python 3.7+
- requests

Install dependencies:
```
pip install requests
```

## Note
AI features will be added in future versions.