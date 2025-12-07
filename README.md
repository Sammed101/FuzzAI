# FuzzAI — v1.0.0
[![license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://www.python.org/)

**A smarter, AI-assisted web fuzzing tool...**
## Quick Start
### 1. Clone the repository
```bash
git clone https://github.com/Sammed101/FuzzAI.git
cd FuzzAI
```
Or download via curl:
```bash
curl -LO https://github.com/Sammed101/FuzzAI/archive/refs/heads/main.zip
unzip main.zip
cd FuzzAI-main
```
### 2. Install dependencies
It is recommended to use a Python virtual environment to avoid package conflicts.
```bash
pip install -r requirements.txt
```
### 3. Run FuzzAI
```bash
python3 fuzzai.py -u https://target.com/FUZZ -w wordlists/test.txt  # Tests if it works correctly
```
❗If any issue occurs while running or installing refer to [Troubleshooting](#troubleshooting).

## Features
🔍 ****AI Wordlist Selection****  
Automatically picks the most relevant wordlist from SecLists based on user intent.

🧠 ****GPT Wordlist Generation****  
Create custom wordlists on the fly using OpenAI (e.g., numbers, patterns, contexts).

 🧹****Advanced Filtering (ffuf-style)****  
 Filter by status codes, response size, lines, or words for cleaner, faster results.

 ⚡****Multi-Threaded Fuzzing****  
 High-speed concurrent requests for efficient endpoint discovery.

✨ ****Colorized, Readable Output****  
Clean terminal formatting to highlight important findings.


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
-h                  # Tool usage and all commands      
```
## Configuration
```bash
# Manually configure the SecLists directory.
# If SecLists is not installed, FuzzAI will prompt you to install it or configure a custom wordlists folder.
python3 fuzzai.py --config-seclists /path/to/SecLists

# Set OpenAI API key (for GPT generation)
python3 fuzzai.py --openai-key YOUR_KEY
```
## Examples
```bash
python3 fuzzai.py -u https://target.com/FUZZ -ai "directories"  # Basic fuzzing with AI wordlist selection
```
```bash
python3 fuzzai.py -u https://FUZZ.target.com -ai "subdomains"   # Subdomain Fuzzing 
```
```bash
python3 fuzzai.py -u https://target.com/FUZZ -gpt "numbers 1-200"  # Wordlist generation
```
```bash
python3 fuzzai.py -u https://target.com/FUZZ -w list.txt  -mc 200  #  Match code 
```
```bash
python3 fuzzai.py -u https://site.com/FUZZ -ai "admin dashboard" -fc 404    # filter unwanted responses
```
```bash
python3 fuzzai.py -u https://api.site.com/v1/FUZZ -ai "rest api" -mc 200,201   # API endpoint enumeration
```
```bash
python3 fuzzai.py -u https://site.com/FUZZ -ai "common quick" -fc 404,403 -t 30 # Fast scan with filters
```
## Troubleshooting
Below are common issues you may encounter while installing or running FuzzAI, along with their solutions.

1]**Error:** ModuleNotFoundError: No module named 'requests'.  
**Cause:** package conflicts  
**Solution:** Run `pip install -r requirements.txt` inside a virtual environment.
```bash
#Using a virtual environment 
python3 -m venv venv
source venv/bin/activate   # make sure it's activated 
pip install -r requirements.txt
```

2]**SecLists not detected**  
**Cause**: Tool cannot find SecLists on the system.  
**Fix:** If you don’t have SecLists installed, FuzzAI will prompt you to install it by pressing 'y' or if your system has a folder that has Wordlists init configure it using command given below.
```bash
python3 fuzzai.py --config-seclists /path/to/SecLists  # Shows the path towards the SecLists
```
To install manually:
```bash
sudo apt install seclists     # Kali Linux / Debian-based
```

Or download manually:
[SecLists](https://github.com/danielmiessler/SecLists) 
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
[![license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
Apache License 2.0 — see LICENSE file.
## Disclaimer
For authorized security testing only. Always obtain permission before testing systems you don't own.
---
## Credits
**Created with ❤️ By [Sammed101](https://github.com/Sammed101) & [Bhaveshs08](https://github.com/Bhaveshs08)**
