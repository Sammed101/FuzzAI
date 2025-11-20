# FuzzAI Project Workspace

This repository is a shared workspace where we will build **FuzzAI**, a Python-based CLI fuzzing tool similar to ffuf.  
The idea is to start simple and then slowly add AI-powered features like intelligent wordlist selection and GPT-style wordlist generation.

Right now, this repo contains:
- The starter CLI fuzzer (`fuzzai.py`)
- Utility modules (HTTP client, wordlist loader)
- Basic folder structure
- A brief project outline inside the `/fuzzai` directory

More features will be added step-by-step as we both contribute.

---


## 📌 Project Brief

**FuzzAI** is a CLI fuzzing tool that:

- Takes a URL containing the keyword `FUZZ`
- Reads a wordlist and replaces `FUZZ` with each word
- Sends requests and shows status code + response length
- Helps identify hidden paths, pages, APIs, etc.

This is the **basic version** — AI-powered features will be added later:
- AI wordlist recommendation
- AI prompt-based wordlist generator (`-gpt`)
- Automated response categorization

This repo will grow as we both contribute.

---

## 🚀 How to Run

```bash
python fuzzai.py -u "https://example.com/FUZZ" -w wordlists/sample.txt -t 10
