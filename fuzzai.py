#!/usr/bin/env python3
"""
FuzzAI - AI-Powered Directory Fuzzing Tool
Main CLI entry point
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path

from utils.logger import setup_logger, log_banner
from utils.config import Config
from utils.wordlist_resolver import WordlistResolver
from ai.selector import AIWordlistSelector
from ai.generator import GPTWordlistGenerator
from core.fuzzer import Fuzzer
from core.filters import ResponseFilter

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='FuzzAI - AI-Powered Directory Fuzzing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic fuzzing:
    fuzzai -u https://target.com/FUZZ -w wordlist.txt

  AI wordlist selection:
    fuzzai -u https://target.com/FUZZ -ai "admin pages"

  GPT wordlist generation:
    fuzzai -u https://target.com/FUZZ -gpt "numbers 1-200"

  With filtering:
    fuzzai -u https://target.com/FUZZ -w list.txt -fc 404 -fs 1234
        """
    )

    # -u is optional here so config-only commands can run
    parser.add_argument('-u', '--url', required=False,
                        help='Target URL with FUZZ keyword (e.g., https://site.com/FUZZ)')

    wordlist_group = parser.add_mutually_exclusive_group()
    wordlist_group.add_argument('-w', '--wordlist',
                                help='Path to wordlist file')
    wordlist_group.add_argument('-ai', '--ai-select',
                                help='AI-assisted wordlist selection (e.g., "admin pages")')
    wordlist_group.add_argument('-gpt', '--gpt-generate',
                                help='Generate wordlist using GPT (e.g., "numbers 1-200")')

    parser.add_argument('-t', '--threads', type=int, default=10,
                        help='Number of concurrent threads (default: 10)')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    parser.add_argument('--delay', type=float, default=0,
                        help='Delay between requests in seconds (default: 0)')

    parser.add_argument('-fc', '--filter-code', type=str,
                        help='Filter by status code (comma-separated, e.g., 404,403)')
    parser.add_argument('-fs', '--filter-size', type=str,
                        help='Filter by response size in bytes (comma-separated)')
    parser.add_argument('-fl', '--filter-lines', type=str,
                        help='Filter by number of lines (comma-separated)')
    parser.add_argument('-fw', '--filter-words', type=str,
                        help='Filter by word count (comma-separated)')

    parser.add_argument('-mc', '--match-code', type=str,
                        help='Match only specific status codes (comma-separated)')
    parser.add_argument('-ms', '--match-size', type=str,
                        help='Match only specific response sizes (comma-separated)')
    parser.add_argument('-ml', '--match-lines', type=str,
                        help='Match only specific line counts (comma-separated)')
    parser.add_argument('-mw', '--match-words', type=str,
                        help='Match only specific word counts (comma-separated)')

    parser.add_argument('-o', '--output',
                        help='Save results to file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output (debug)')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output')

    parser.add_argument('--config-seclists',
                        help='Set SecLists installation path')
    parser.add_argument('--openai-key',
                        help='Set OpenAI API key for GPT generation')

    parser.add_argument('--insecure', action='store_true',
                        help='Disable TLS certificate verification (insecure)')

    return parser.parse_args()

def validate_url(url, logger):
    """Validate URL contains FUZZ keyword (uses logger for errors)"""
    if not url or 'FUZZ' not in url:
        logger.error("URL must contain FUZZ keyword")
        sys.exit(1)

    if not url.startswith(('http://', 'https://')):
        logger.error("URL must start with http:// or https://")
        sys.exit(1)

def ensure_seclists_available(config, logger):
    """
    Robust SecLists availability check + interactive installer.
    Order:
      1. Check Config.get_seclists_path() (highest priority)
      2. Check env FUZZAI_SECLISTS
      3. Check project-local and common system locations
      4. Offer interactive install only if nothing found

    Returns True if we have a configured and existing SecLists directory.
    """
    def _normalize_and_check(p):
        if not p:
            return None
        p = os.path.expanduser(str(p))
        p = os.path.abspath(p)
        return p if os.path.isdir(p) else None

    # 1) Configured path (preferred) — CHECK FIRST and return if usable
    try:
        cfg_raw = None
        if hasattr(config, "get_seclists_path"):
            cfg_raw = config.get_seclists_path()
        else:
            cfg_raw = getattr(config, "seclists_path", None)
    except Exception:
        cfg_raw = None

    if cfg_raw:
        cfg_path = _normalize_and_check(cfg_raw)
        if cfg_path:
            # persist normalized path back to config if setter exists
            try:
                if hasattr(config, "set_seclists_path"):
                    config.set_seclists_path(cfg_path)
            except Exception:
                pass
            logger.debug(f"[DEBUG] SecLists configured in config: {cfg_path} (exists)")
            return True
        else:
            logger.debug(f"[DEBUG] SecLists configured in config but path not found or not a directory: {cfg_raw}")

    # 2) Environment override
    env_raw = os.environ.get("FUZZAI_SECLISTS")
    if env_raw:
        env_path = _normalize_and_check(env_raw)
        if env_path:
            try:
                if hasattr(config, "set_seclists_path"):
                    config.set_seclists_path(env_path)
            except Exception:
                pass
            logger.debug(f"[DEBUG] Found SecLists via FUZZAI_SECLISTS: {env_path}")
            return True
        else:
            logger.debug(f"[DEBUG] FUZZAI_SECLISTS set but path invalid: {env_raw}")

    # 3) Project-local and common system locations
    project_local = os.path.abspath("./SecLists")
    common_paths = [
        project_local,
        "/usr/share/seclists",
        "/usr/share/wordlists/SecLists",
        str(Path.home() / "SecLists"),
        "/opt/SecLists",
    ]

    for p in common_paths:
        p_norm = _normalize_and_check(p)
        logger.debug(f"[DEBUG] Checking possible SecLists location: {p}")
        if p_norm:
            # Found an installation; ask user whether to configure it
            try:
                answer = input(f"✓ Found SecLists at: {p_norm}\n\n📍 Would you like to configure this path? (y/n): ").strip().lower()
            except EOFError:
                # Non-interactive environment — persist automatically
                try:
                    if hasattr(config, "set_seclists_path"):
                        config.set_seclists_path(p_norm)
                except Exception:
                    pass
                logger.debug(f"[DEBUG] Non-interactive: auto-configured SecLists: {p_norm}")
                return True

            if answer.startswith("y"):
                try:
                    if hasattr(config, "set_seclists_path"):
                        config.set_seclists_path(p_norm)
                except Exception:
                    pass
                logger.info(f"SecLists path configured: {p_norm}")
                return True
            else:
                logger.debug("[DEBUG] User chose not to configure the detected SecLists path.")
                # Continue scanning other possible locations
                continue

    # 4) Nothing found — offer interactive install
    logger.debug("[DEBUG] SecLists not found in configured, env or common locations.")
    try:
        answer = input("📥 Would you like to install SecLists now? (y/n): ").strip().lower()
    except EOFError:
        logger.debug("[DEBUG] Non-interactive environment, skipping installation prompt.")
        return False

    if not answer.startswith('y'):
        logger.info("User declined to install SecLists now.")
        return False

    # Install into ~/SecLists by default
    target_dir = str(Path.home() / "SecLists")
    if os.path.isdir(target_dir):
        try:
            if hasattr(config, "set_seclists_path"):
                config.set_seclists_path(target_dir)
        except Exception:
            pass
        logger.info(f"SecLists path configured: {target_dir}")
        return True

    git_url = "https://github.com/danielmiessler/SecLists.git"
    logger.info(f"Cloning SecLists into {target_dir} ...")
    try:
        result = subprocess.run(["git", "clone", "--depth", "1", git_url, target_dir],
                                check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error("Failed to clone SecLists.")
            try:
                logger.debug(result.stdout)
                logger.debug(result.stderr)
            except Exception:
                pass
            return False
        try:
            if hasattr(config, "set_seclists_path"):
                config.set_seclists_path(target_dir)
        except Exception:
            pass
        logger.info(f"SecLists path configured: {target_dir}")
        return True
    except Exception as e:
        logger.error(f"Exception while installing SecLists: {e}")
        return False

def main():
    args = parse_arguments()

    # If user only wants to set config or openai key, allow that without requiring -u
    if not (args.config_seclists or args.openai_key) and not args.url:
        print("Error: -u/--url is required unless using --config-seclists or --openai-key")
        sys.exit(1)

    # Setup logger
    logger = setup_logger(verbose=args.verbose, no_color=args.no_color)
    log_banner()

    # Initialize configuration
    config = Config()

    # --- Clean SecLists config verification (DEBUG only, no noise in normal mode) ---
    try:
        if hasattr(config, "get_seclists_path"):
            cfg = config.get_seclists_path()
        else:
            cfg = getattr(config, "seclists_path", None)

        if cfg:
            cfg_norm = os.path.abspath(os.path.expanduser(str(cfg)))
            if os.path.isdir(cfg_norm):
                try:
                    if hasattr(config, "set_seclists_path"):
                        config.set_seclists_path(cfg_norm)
                except Exception:
                    pass
                logger.debug(f"[DEBUG] Configured SecLists path valid: {cfg_norm}")
            else:
                logger.debug(f"[DEBUG] Config has SecLists path but directory missing: {cfg}")
        else:
            logger.debug("[DEBUG] No SecLists path configured")
    except Exception as e:
        logger.debug(f"[DEBUG] Could not validate SecLists path: {e}")

    # Handle configuration commands
    if args.config_seclists:
        # normalize and persist
        p = os.path.expanduser(str(args.config_seclists))
        p = os.path.abspath(p)
        if not os.path.isdir(p):
            logger.warning(f"Provided path does not exist or is not a directory: {p}")
            # still set it so user can update later
        try:
            if hasattr(config, "set_seclists_path"):
                config.set_seclists_path(p)
            else:
                setattr(config, "seclists_path", p)
        except Exception:
            logger.debug("Could not persist seclists path via config.set_seclists_path()")
        logger.info(f"SecLists path configured: {p}")
        return

    if args.openai_key:
        try:
            if hasattr(config, "set_openai_key"):
                config.set_openai_key(args.openai_key)
            else:
                setattr(config, "openai_key", args.openai_key)
        except Exception:
            logger.debug("Could not persist openai key via config.set_openai_key()")
        logger.info("OpenAI API key configured successfully")
        return

    # Validate URL
    validate_url(args.url, logger)

    # Determine wordlist path
    wordlist_path = None

    if args.wordlist:
        # Use provided wordlist
        wordlist_path = args.wordlist
        if not os.path.isfile(wordlist_path):
            logger.error(f"Wordlist not found: {wordlist_path}")
            sys.exit(1)
        logger.info(f"Using wordlist: {wordlist_path}")

    elif args.ai_select:
        # AI-assisted wordlist selection
        logger.info(f"🤖 AI selecting wordlist for: '{args.ai_select}'")
        resolver = WordlistResolver(config)
        selector = AIWordlistSelector(resolver)

        # Ensure SecLists is configured or installed, interactively if needed
        seclists_ok = ensure_seclists_available(config, logger)
        if not seclists_ok and not (hasattr(config, "get_seclists_path") and config.get_seclists_path()):
            logger.warning("SecLists not configured. Selector may fail to find suitable wordlists.")

        # Attempt selection (selector should consult resolver which uses config.get_seclists_path())
        wordlist_path = selector.select_wordlist(args.ai_select)

        if not wordlist_path:
            logger.error("No suitable wordlist found. Please:")
            logger.error("  1. Install SecLists: git clone https://github.com/danielmiessler/SecLists")
            logger.error("  2. Configure path: fuzzai --config-seclists /path/to/SecLists")
            logger.error("  3. Or provide custom wordlist: fuzzai -u URL -w wordlist.txt")
            sys.exit(1)

        # Show short basename in normal runs; full path in verbose mode
        # Show short basename in normal runs; full path in verbose mode
        try:
            display_path = wordlist_path if args.verbose else os.path.basename(wordlist_path)
        except Exception:
            display_path = wordlist_path
        logger.success(f"✓ Generated wordlist: {display_path}")
        if args.verbose:
            logger.debug(f"[DEBUG] Full generated wordlist path: {wordlist_path}")


    elif args.gpt_generate:
        # GPT wordlist generation
        logger.info(f"🤖 Generating wordlist with GPT: '{args.gpt_generate}'")

        api_key = None
        try:
            if hasattr(config, "get_openai_key"):
                api_key = config.get_openai_key()
            else:
                api_key = getattr(config, "openai_key", None)
        except Exception:
            api_key = None

        if not api_key:
            logger.error("OpenAI API key not configured. Set it with:")
            logger.error("  fuzzai --openai-key YOUR_API_KEY")
            sys.exit(1)

        generator = GPTWordlistGenerator(api_key)
        wordlist_path = generator.generate(args.gpt_generate)

        if not wordlist_path:
            logger.error("Failed to generate wordlist")
            sys.exit(1)

        try:
            display_path = wordlist_path if args.verbose else os.path.basename(wordlist_path)
        except Exception:
            display_path = wordlist_path
        logger.success(f"✓ Generated wordlist: {display_path}")
        if args.verbose:
            logger.debug(f"[DEBUG] Full generated wordlist path: {wordlist_path}")

    else:
        logger.error("No wordlist specified. Use -w, -ai, or -gpt")
        sys.exit(1)

    # Setup filters
    response_filter = ResponseFilter(
        filter_codes=args.filter_code,
        filter_sizes=args.filter_size,
        filter_lines=args.filter_lines,
        filter_words=args.filter_words,
        match_codes=args.match_code,
        match_sizes=args.match_size,
        match_lines=args.match_lines,
        match_words=args.match_words
    )

    # Initialize and run fuzzer
    fuzzer = Fuzzer(
        url=args.url,
        wordlist_path=wordlist_path,
        threads=args.threads,
        timeout=args.timeout,
        delay=args.delay,
        response_filter=response_filter,
        output_file=args.output,
        verbose=args.verbose
    )

    try:
        fuzzer.run()
    except KeyboardInterrupt:
        logger.warning("\n🛑 Fuzzing interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
