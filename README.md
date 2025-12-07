# FuzzAI 🤖

**AI-Powered Fuzzing Tool**

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Basic fuzzing with AI wordlist selection
python3 fuzzai.py -u https://target.com/FUZZ -ai "admin pages"

# With custom wordlist
python3 fuzzai.py -u https://target.com/FUZZ -w wordlist.txt

# GPT wordlist generation
python3 fuzzai.py -u https://target.com/FUZZ -gpt "numbers 1-200"

# With filtering
python3 fuzzai.py -u https://target.com/FUZZ -w list.txt -fc 404 -mc 200
```

## Features

**AI Wordlist Selection** - Let AI choose the best wordlist  
**GPT Generation** - Generate custom wordlists with OpenAI  
**Advanced Filtering** - ffuf-style filtering (status, size, lines, words)  
**Multi-threaded** - Fast concurrent fuzzing  
**Colorized Output** - Beautiful terminal display  

## Commands

```bash
-u URL              # Target URL with FUZZ keyword (required)
-w FILE             # Wordlist file path
-ai "PROMPT"        # AI wordlist selection
-gpt "PROMPT"       # GPT wordlist generation
-t NUM              # Number of threads (default: 10)
-fc CODES           # Filter status codes (e.g., -fc 404,403)
-fs SIZES           # Filter response sizes
-mc CODES           # Match only specific codes
-o FILE             # Save results to file
-v                  # Verbose mode
```

## Configuration

```bash
# Set SecLists path (for AI selection)
python3 fuzzai.py --config-seclists /path/to/SecLists

# Set OpenAI API key (for GPT generation)
python3 fuzzai.py --openai-key YOUR_KEY
# Or: export OPENAI_API_KEY=YOUR_KEY
```

## Examples

```bash
# Admin panel discovery
python3 fuzzai.py -u https://site.com/FUZZ -ai "admin dashboard" -fc 404

# API endpoint enumeration
python3 fuzzai.py -u https://api.site.com/v1/FUZZ -ai "rest api" -mc 200,201

# Custom number range
python3 fuzzai.py -u https://site.com/user/FUZZ -gpt "numbers 1-1000" -t 50

# Fast scan with filters
python3 fuzzai.py -u https://site.com/FUZZ -ai "common quick" -fc 404,403 -t 30
```

## Project Structure

```
FuzzAI/
├── fuzzai.py                 # Main CLI
├── core/
│   ├── fuzzer.py            # Fuzzing engine
│   └── filters.py           # Response filtering
├── utils/
│   ├── config.py            # Configuration
│   ├── logger.py            # Logging
│   └── wordlist_resolver.py # Wordlist discovery
├── ai/
│   ├── selector.py          # AI selection
│   └── generator.py         # GPT generation
└── wordlists/
    └── generated/           # Generated wordlists
```

## License

Apache License 2.0 — see LICENSE file.

## Disclaimer

For authorized security testing only. Always obtain permission before testing systems you don't own.

---

**Created with ❤️ By Sammed101 & Bhaveshs08**
