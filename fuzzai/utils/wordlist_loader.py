# Load a wordlist file and return a list of words
# Each word is stripped of whitespace and empty lines are ignored
def load_wordlist(path):
    words = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word:
                    words.append(word)
        return words
    except Exception as e:
        raise Exception(f"Failed to load wordlist: {e}")
