"""
AI-powered selector for wordlists.

Implements intent mapping, token expansion, generation detection,
scoring across folder weight, token overlap, and size preferences.

Public API:
- select_top_candidates(prompt: str, n: int=3) -> List[Dict]
- select_wordlist(prompt: str) -> Optional[str]
- explain_selection(prompt: str, path: str) -> str

Generator action returned when prompt implies generation (e.g. "1-200").
"""

import re
import math
from typing import List, Dict, Optional, Tuple
from utils.logger import get_logger


class AIWordlistSelector:
    def __init__(self, wordlist_resolver):
        self.resolver = wordlist_resolver
        self.logger = get_logger()

        # Synonyms / token expansions
        self.synonyms = {
            'admin': ['admin', 'panel', 'dashboard', 'cpanel', 'backend', 'manager'],
            'login': ['login', 'auth', 'signin', 'signin', 'logout', 'credentials', 'authn', 'authz'],
            'api': ['api', 'endpoint', 'rest', 'swagger', 'graphql', 'jsonrpc'],
            'username': ['user', 'username', 'users', 'account', 'accounts', 'profile'],
            'directory': ['dir', 'directory', 'folder', 'path'],
            'file': ['file', 'backup', 'bak', 'config', 'conf', 'extension'],
            'cms': ['wordpress', 'drupal', 'joomla', 'magento', 'cms'],
            'numbers': ['numbers', 'range'],
            'quick': ['quick', 'small', 'fast', 'short'],
            'comprehensive': ['comprehensive', 'thorough', 'large', 'extensive', 'big'],
            'subdomain': ['subdomain', 'subdomains', 'sub-domain', 'hosts', 'hostname']
        }

        # Folder-priority table (primary weight)
        # Keys represent fragments often found in SecLists paths or categories
        self.folder_weights = {
            'discovery/web-content': 3.0,
            'web-content': 3.0,
            'discovery': 2.5,
            'raft': 2.5,
            'dirbuster': 2.5,
            'api': 3.0,
            'user': 2.0,
            'usernames': 2.0,
            'password': 1.0,
            'file-extensions': 1.5,
            'cms': 2.0,
            'dns': 2.5,
            'subdomain': 3.0,
            'generic': 1.0,
            'other': 0.5,
        }

        # Default fallback candidates to prefer when no direct match
        self.fallback_priority = [
            'common.txt',
            'directory-list-2.3-medium.txt',
            'raft-medium-directories.txt'
        ]

    # ----------------------------- Public API -----------------------------
    def select_top_candidates(self, prompt: str, n: int = 3) -> List[Dict]:
        """Return top N candidate wordlists or a generator action.

        Each candidate dict contains: path, filename, size, score, reason, explanation
        If prompt implies generation, returns a single dict with action details.
        """
        prompt = (prompt or '').strip()
        self.logger.debug(f"Selecting top candidates for prompt: '{prompt}'")

        # Generation detection (numbers / ranges)
        gen = self._detect_generation_request(prompt)
        if gen:
            self.logger.debug("Detected generation request")
            return [gen]

        # Tokenize & expand
        tokens = self._tokenize_and_expand(prompt)
        size_pref = self._detect_size_preference(prompt)

        # Ask resolver for candidates (keyword search) first
        try:
            resolver_candidates = self.resolver.search_by_keywords(tokens, limit=50)
        except Exception:
            resolver_candidates = []

        all_wordlists = self.resolver.find_all_wordlists()

        # If resolver returned none, use all as fallback
        if not resolver_candidates:
            self.logger.debug("No direct resolver matches, using full list as candidates")
            resolver_candidates = all_wordlists

        # Compute scores using combined mental models
        scored = self._score_candidates(resolver_candidates, tokens, size_pref)

        if not scored:
            # Fallback to popular lists
            self.logger.debug("No scored candidates, applying fallback popular lists")
            fallback = self._get_fallback_candidates(all_wordlists)
            scored = self._score_candidates(fallback, tokens, size_pref)

        # Normalize scores and build explanations
        normalized = self._normalize_and_explain(scored, prompt, tokens, size_pref)

        # Return top-n
        return normalized[:max(1, n)]

    def select_wordlist(self, prompt: str) -> Optional[str]:
        """Return the single top path or None."""
        top = self.select_top_candidates(prompt, n=1)
        if not top:
            return None
        candidate = top[0]
        if 'action' in candidate and candidate.get('action') == 'generate':
            # generation action → no path
            return None
        return candidate.get('path')

    def explain_selection(self, prompt: str, path: str) -> str:
        """Human-friendly multi-line explanation for a selection."""
        all_wordlists = self.resolver.find_all_wordlists()
        w = next((x for x in all_wordlists if x['path'] == path or x['filename'] == path), None)
        if not w:
            return f"No explanation available for '{path}'"

        # Recompute components for this single candidate to produce the explanation
        tokens = self._tokenize_and_expand(prompt)
        size_pref = self._detect_size_preference(prompt)
        score_components = self._compute_score_components(w, tokens, size_pref)

        lines = [
            f"Selected: {w['filename']}",
            f"Path: {w['path']}",
            f"Category: {w.get('category', 'unknown')}",
            f"Size: {w['size']} bytes",
            "",
            "Reasoning breakdown:",
            f"- folder_weight={score_components['folder_weight']:.2f}",
            f"- token_overlap={score_components['token_overlap']:.2f}",
            f"- size_score={score_components['size_score']:.2f}",
            f"- raw_score={score_components['raw_score']:.2f}",
            "",
            score_components['explanation']
        ]

        return "\n".join(lines)

    # --------------------------- Internal helpers -------------------------
    def _tokenize_and_expand(self, prompt: str) -> List[str]:
        """Lowercase, strip punctuation, extract tokens, expand with synonyms."""
        s = (prompt or '').lower()
        # Remove punctuation except . and - and .. which may be in ranges handled elsewhere
        s_clean = re.sub(r'[.,;:!?()]', ' ', s)

        # Extract words of length >=2
        tokens = re.findall(r"\b[0-9a-zA-Z\-_.]{2,}\b", s_clean)

        # Normalize tokens (strip separators)
        normalized = [t.strip('-_.') for t in tokens if t.strip('-_.')]

        # Common typo corrections
        typo_corrections = {
            'suddomain': 'subdomain',
            'subomain': 'subdomain',
            'adm1n': 'admin',
            'adminl': 'admin',
            'aapi': 'api',
        }
        
        corrected = []
        for t in normalized:
            if t in typo_corrections:
                corrected.append(typo_corrections[t])
            else:
                corrected.append(t)
        
        normalized = corrected

        # Expand tokens with synonyms map
        expanded = set(normalized)
        for t in normalized:
            for key, syns in self.synonyms.items():
                if t == key or t in syns:
                    expanded.update(syns)
                    expanded.add(key)

        return list(expanded)

    def _detect_size_preference(self, prompt: str) -> str:
        p = (prompt or '').lower()
        if any(x in p for x in ['quick', 'small', 'fast', 'short']):
            return 'small'
        if any(x in p for x in ['comprehensive', 'large', 'thorough', 'extensive']):
            return 'large'
        return 'medium'

    def _detect_generation_request(self, prompt: str) -> Optional[Dict]:
        """Detect requests like 'numbers 1-200', '1..99', 'list 1 to 100'."""
        if not prompt:
            return None

        # patterns: 1-200, 1..200, 1 to 200
        m = re.search(r"\b(\d+)\s*(?:-|\.\.|to)\s*(\d+)\b", prompt)
        if m:
            start = int(m.group(1))
            end = int(m.group(2))
            if start > end:
                start, end = end, start
            return {
                'action': 'generate',
                'generator': 'range',
                'start': start,
                'end': end,
                'format': 'one-per-line',
                'explanation': f"Detected numeric range {start}-{end}; generation is preferred over selecting an existing file."
            }

        # 'numbers 1 to 100' spelled out
        m2 = re.search(r"numbers?\s*(\d+)\s*(?:-|to|until)\s*(\d+)", prompt)
        if m2:
            start = int(m2.group(1)); end = int(m2.group(2))
            if start > end:
                start, end = end, start
            return {
                'action': 'generate',
                'generator': 'range',
                'start': start,
                'end': end,
                'format': 'one-per-line',
                'explanation': f"Detected numeric range {start}-{end}; generation is preferred." 
            }

        return None

    def _score_candidates(self, candidates: List[Dict], tokens: List[str], size_pref: str) -> List[Dict]:
        scored = []
        
        # Detect if this is an admin/directory discovery intent (high priority for broad lists)
        is_discovery_intent = any(t in tokens for t in ['admin', 'directory', 'api', 'login', 'auth', 'panel', 'dashboard'])
        
        for c in candidates:
            try:
                comps = self._compute_score_components(c, tokens, size_pref, is_discovery_intent)
                scored.append({
                    **c,
                    'raw_score': comps['raw_score'],
                    'folder_weight': comps['folder_weight'],
                    'token_overlap': comps['token_overlap'],
                    'size_score': comps['size_score'],
                    'explanation_comp': comps['explanation']
                })
            except Exception:
                continue

        # Sort by raw_score desc then by size (prefer medium/appropriate)
        scored.sort(key=lambda x: (-x['raw_score'], x.get('size', 0)))
        return scored

    def _compute_score_components(self, candidate: Dict, tokens: List[str], size_pref: str, is_discovery_intent: bool = False) -> Dict:
        """Compute folder_weight, token_overlap, size_score and combined raw_score."""
        path = candidate.get('path', '').lower()
        filename = candidate.get('filename', '').lower()
        rel = candidate.get('relative_path', '').lower()
        category = candidate.get('category', '').lower()

        # Folder weight: inspect category first, then path fragments
        folder_weight = 0.0
        # category-based boost
        if category:
            folder_weight = max(folder_weight, self.folder_weights.get(category, 0.0))

        for frag, w in self.folder_weights.items():
            if frag in path or frag in rel or frag in filename:
                folder_weight = max(folder_weight, w)

        # Token overlap: fraction of tokens appearing in filename or relative path
        if tokens:
            hits = 0
            searchable = ' '.join([filename, rel, path])
            for t in tokens:
                t_clean = t.lower()
                if t_clean in searchable:
                    hits += 1
            token_overlap = hits / max(1, len(tokens))
        else:
            token_overlap = 0.0

        # Size score: prefer medium by default; small/large preferences adjust
        size = candidate.get('size', 0)
        size_score = self._size_score(size, size_pref)

        # Coverage bonus: prefer broad lists like common.txt, raft-medium, directory-list
        # over specialized/narrow ones like API-specific or single-vendor lists
        coverage_bonus = 0.0
        coverage_penalty = 0.0
        
        # Strong preference for well-known broad discovery lists
        if filename in ['common.txt', 'raft-medium-directories.txt', 'directory-list-2.3-medium.txt', 
                        'raft-medium-words.txt', 'big.txt']:
            coverage_bonus = 6.0  # highest bonus for these well-known broad lists
        elif any(x in filename for x in ['raft-medium', 'directory-list', 'dirbuster']):
            coverage_bonus = 4.0  # bonus for other raft/dirbuster variants
        elif any(x in filename.lower() for x in ['subdomain', 'dns']):
            # Bonus for subdomain/DNS lists when searching for subdomains
            # But penalize language-specific variants (Italian, Spanish, French, German, etc.)
            if any(x in filename.lower() for x in ['italian', 'spanish', 'french', 'german', 'portuguese', 'russian', 'dutch', 'polish', 'japanese', 'chinese', 'arabic']):
                coverage_penalty = -4.0  # strong penalty for language-specific lists
            else:
                coverage_bonus = 5.0
        elif any(x in filename for x in ['common']):
            # Penalize specialized variants if they have "common" in the name
            if any(x in filename for x in ['admin', 'base64', 'base32', 'hex', 'servlet', 'jsp', 'aspx', 'php', 'java', 'rails', 'wordpress']):
                coverage_penalty = -2.5  # penalize technology/purpose-specific variants
            else:
                coverage_bonus = 3.0  # bonus for plain common lists
        
        # Penalty for overly specialized paths (e.g., Service-Specific, vendor-specific, API-only, Technology-specific)
        if coverage_penalty == 0.0:  # only apply if not already penalized
            if any(x in path for x in ['/api/', 'service-specific', 'vendor', 'ispsystem', 'oauth', 'specific', 'java', 'rails', 'cms']):
                # Only penalize if it looks narrowly scoped
                if not any(x in filename for x in ['raft', 'directory-list', 'common.txt', 'subdomain', 'dns']):
                    coverage_penalty = -2.5  # increased penalty for specialized lists
                    if is_discovery_intent:
                        coverage_penalty = -3.5  # harsher penalty when doing discovery

        # Combine with weights (folder dominates)
        raw_score = (folder_weight * 2.0) + (token_overlap * 1.0) + (size_score * 0.5) + coverage_bonus + coverage_penalty

        explanation = (
            f"folder_weight={folder_weight:.2f}, token_overlap={token_overlap:.2f}, "
            f"size_score={size_score:.2f}, coverage_bonus={coverage_bonus:.2f}, "
            f"coverage_penalty={coverage_penalty:.2f} -> raw_score={raw_score:.2f}"
        )

        return {
            'folder_weight': folder_weight,
            'token_overlap': token_overlap,
            'size_score': size_score,
            'raw_score': raw_score,
            'explanation': explanation
        }

    def _size_score(self, size: int, size_pref: str) -> float:
        """Map file size to a score in [0,1] according to preference."""
        # Interpret sizes (bytes)
        # small: <50KB, medium: 50KB-1MB, large: >1MB
        if size <= 0:
            return 0.0

        kb = size / 1024.0
        if size_pref == 'small':
            # prefer smaller sizes
            return max(0.0, 1.0 - (kb / 200.0))  # drops off after ~200KB
        if size_pref == 'large':
            # prefer bigger sizes
            return math.tanh(kb / 1024.0)  # grows with MBs
        # medium
        # ideal around 100KB-1MB
        ideal = 200.0  # KB
        score = 1.0 / (1.0 + abs(kb - ideal) / ideal)
        return max(0.0, min(1.0, score))

    def _normalize_and_explain(self, scored: List[Dict], prompt: str, tokens: List[str], size_pref: str) -> List[Dict]:
        if not scored:
            return []

        # Normalize raw_score to 0..5 scale for readability
        raw_scores = [c['raw_score'] for c in scored]
        min_s = min(raw_scores); max_s = max(raw_scores)
        span = max(1e-6, max_s - min_s)

        normalized = []
        for c in scored:
            norm = 5.0 * (c['raw_score'] - min_s) / span
            reason = c.get('explanation_comp') or c.get('explanation', '')
            explanation = (
                f"Selected because folder_weight dominates intent mapping; {reason}. "
                f"Prompt preference: {size_pref}."
            )

            normalized.append({
                'path': c.get('path'),
                'filename': c.get('filename'),
                'size': c.get('size'),
                'score': round(norm, 3),
                'reason': reason,
                'explanation': explanation
            })

        # Sort by normalized score desc
        normalized.sort(key=lambda x: -x['score'])
        return normalized

    def _get_fallback_candidates(self, all_wordlists: List[Dict]) -> List[Dict]:
        # Prefer matching popular filenames
        matches = []
        for w in all_wordlists:
            name = w['filename'].lower()
            if any(p in name for p in self.fallback_priority):
                matches.append(w)

        # If none, just return a few smallest/generic ones
        if not matches:
            sorted_all = sorted(all_wordlists, key=lambda x: x.get('size', 0))
            return sorted_all[:10]

        return matches