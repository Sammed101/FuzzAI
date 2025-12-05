#!/usr/bin/env python3
"""
FuzzAI - AI-Powered Fuzzing Tool
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

def print_help_menu():
    """Print FuzzAI help menu """
    
    log_banner()

    help_text = """FuzzAI - AI-Powered Fuzzing Tool

  
HTTP OPTIONS:
  -u, --url               Target URL with FUZZ keyword (e.g., https://site.com/FUZZ)
  -H, --header            Custom HTTP header (e.g., "User-Agent: Mozilla/5.0")
  -X, --method            HTTP method to use (default: GET)
  -b, --data              POST data / request body
  -d, --data-ascii        POST data in ASCII format
  -k, --insecure          Disable TLS certificate verification (insecure)
  --timeout               Request timeout in seconds (default: 10)
  --delay                 Delay between requests in seconds (default: 0)
  -r, --follow-redirect   Follow HTTP redirects
  --proxy                 Use proxy (e.g., http://127.0.0.1:8080)

WORDLIST OPTIONS:
  -w, --wordlist          Path to wordlist file
  -ai, --ai-select        AI-assisted wordlist selection (e.g., "admin pages")
  -gpt, --gpt-generate    Generate wordlist using GPT (e.g., "numbers 1-200")
  -e, --extensions        File extensions to add (comma-separated, e.g., .php,.html)
  -D, --data-source       Use data source for generation (API, file, etc.)

MATCHER OPTIONS:
  -mc, --match-code       Match only specific status codes (comma-separated)
  -ms, --match-size       Match only specific response sizes (comma-separated)
  -ml, --match-lines      Match only specific line counts (comma-separated)
  -mw, --match-words      Match only specific word counts (comma-separated)
  -mr, --match-regex      Match response body by regex pattern
  -mmode                  Matcher logic mode: or/and (default: or)

FILTER OPTIONS:
  -fc, --filter-code      Filter by status code (comma-separated, e.g., 404,403)
  -fs, --filter-size      Filter by response size in bytes (comma-separated)
  -fl, --filter-lines     Filter by number of lines (comma-separated)
  -fw, --filter-words     Filter by word count (comma-separated)
  -fr, --filter-regex     Filter response body by regex pattern
  -fmode                  Filter logic mode: or/and (default: or)

OUTPUT OPTIONS:
  -o, --output            Save results to file
  -of, --output-format    Output format: csv, json, html, txt (default: txt)
  -od, --output-dir       Output directory for results (default: ./results)
  -v, --verbose           Verbose output with debug information
  --no-color              Disable colored output
  --json                  Output results as JSON to stdout

GENERAL OPTIONS:
  -t, --threads           Number of concurrent threads (default: 10)
  -rate, --rate           Request rate limit (requests per second)
  -maxtime                Maximum execution time in seconds
  -c, --colored           Colored output (default: enabled)
  -s, --silent            Silent mode (only show results)
  -p, --progress          Show progress bar
  -V, --version           Show version information
  -h, --help              Show this help message

AI OPTIONS:
  --config-seclists       Set SecLists installation path
  --openai-key            Set OpenAI API key for GPT generation
  --ai-mode               AI selection mode: smart, broad, narrow (default: smart)
  --explain               Explain why a wordlist was selected

ADVANCED OPTIONS:
  --config                Load configuration from file
  --save-config           Save current options to config file
  --request               HTTP request file (raw format)
  --recursion             Enable recursion (subdirectory fuzzing)
  --recursion-depth       Maximum recursion depth (default: 1)
  --sni                   Server Name Indication (SNI) for TLS
  --http2                 Use HTTP/2 protocol

EXAMPLE USAGE:
  Basic fuzzing:
    fuzzai -u https://target.com/FUZZ -w wordlist.txt

  AI wordlist selection:
    fuzzai -u https://target.com/FUZZ -ai "admin pages"

  Match specific codes, filter 404s:
    fuzzai -u https://target.com/FUZZ -w list.txt -mc 200 -fc 404

  GPT wordlist generation:
    fuzzai -u https://target.com/FUZZ -gpt "numbers 1-200"

  Custom headers and POST data:
    fuzzai -u https://target.com/FUZZ -w list.txt -H "Authorization: Bearer TOKEN" -X POST -b "param=FUZZ"

  Output as JSON with progress:
    fuzzai -u https://target.com/FUZZ -ai "api endpoints" -of json -p

For more information and documentation: https://github.com/Sammed101/fuzzai
"""
    print(help_text)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='FuzzAI - AI-Powered Fuzzing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        epilog="Use -h or --help for detailed help menu"
    )

    # Help option (custom)
    parser.add_argument('-h', '--help', action='store_true',
                        help='Show this help message')

    # HTTP OPTIONS
    http_group = parser.add_argument_group('HTTP OPTIONS', 'Options controlling the HTTP request')
    http_group.add_argument('-u', '--url', required=False,
                        help='Target URL with FUZZ keyword (e.g., https://site.com/FUZZ)')
    http_group.add_argument('-H', '--header', action='append', default=[],
                        help='Custom HTTP header (can be used multiple times)')
    http_group.add_argument('-X', '--method', default='GET',
                        help='HTTP method to use (default: GET)')
    http_group.add_argument('-b', '--data',
                        help='POST data / request body')
    http_group.add_argument('-d', '--data-ascii',
                        help='POST data in ASCII format')
    http_group.add_argument('-k', '--insecure', action='store_true',
                        help='Disable TLS certificate verification')
    http_group.add_argument('--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    http_group.add_argument('--delay', type=float, default=0,
                        help='Delay between requests in seconds (default: 0)')
    http_group.add_argument('-r', '--follow-redirect', action='store_true',
                        help='Follow HTTP redirects')
    http_group.add_argument('--proxy',
                        help='Use proxy (e.g., http://127.0.0.1:8080)')
    http_group.add_argument('--sni',
                        help='Server Name Indication (SNI) for TLS')

    # WORDLIST OPTIONS
    wordlist_group = parser.add_argument_group('WORDLIST OPTIONS', 'Wordlist sources and generation')
    wl_source = wordlist_group.add_mutually_exclusive_group()
    wl_source.add_argument('-w', '--wordlist',
                        help='Path to wordlist file')
    wl_source.add_argument('-ai', '--ai-select',
                        help='AI-assisted wordlist selection (e.g., "admin pages")')
    wl_source.add_argument('-gpt', '--gpt-generate',
                        help='Generate wordlist using GPT (e.g., "numbers 1-200")')
    wordlist_group.add_argument('-e', '--extensions', type=str,
                        help='File extensions to add (comma-separated)')
    wordlist_group.add_argument('-D', '--data-source',
                        help='Use data source for generation (API, file, etc.)')

    # MATCHER OPTIONS
    match_group = parser.add_argument_group('MATCHER OPTIONS', 'Matchers for response filtering')
    match_group.add_argument('-mc', '--match-code', type=str,
                        help='Match only specific status codes (comma-separated)')
    match_group.add_argument('-ms', '--match-size', type=str,
                        help='Match only specific response sizes (comma-separated)')
    match_group.add_argument('-ml', '--match-lines', type=str,
                        help='Match only specific line counts (comma-separated)')
    match_group.add_argument('-mw', '--match-words', type=str,
                        help='Match only specific word counts (comma-separated)')
    match_group.add_argument('-mr', '--match-regex', type=str,
                        help='Match response body by regex pattern')
    match_group.add_argument('-mmode', '--match-mode', default='or', choices=['or', 'and'],
                        help='Matcher logic mode: or/and (default: or)')

    # FILTER OPTIONS
    filter_group = parser.add_argument_group('FILTER OPTIONS', 'Filters for response filtering')
    filter_group.add_argument('-fc', '--filter-code', type=str,
                        help='Filter by status code (comma-separated, e.g., 404,403)')
    filter_group.add_argument('-fs', '--filter-size', type=str,
                        help='Filter by response size in bytes (comma-separated)')
    filter_group.add_argument('-fl', '--filter-lines', type=str,
                        help='Filter by number of lines (comma-separated)')
    filter_group.add_argument('-fw', '--filter-words', type=str,
                        help='Filter by word count (comma-separated)')
    filter_group.add_argument('-fr', '--filter-regex', type=str,
                        help='Filter response body by regex pattern')
    filter_group.add_argument('-fmode', '--filter-mode', default='or', choices=['or', 'and'],
                        help='Filter logic mode: or/and (default: or)')

    # OUTPUT OPTIONS
    output_group = parser.add_argument_group('OUTPUT OPTIONS', 'Output and result formatting')
    output_group.add_argument('-o', '--output',
                        help='Save results to file')
    output_group.add_argument('-of', '--output-format', default='txt', 
                        choices=['csv', 'json', 'html', 'txt'],
                        help='Output format: csv, json, html, txt (default: txt)')
    output_group.add_argument('-od', '--output-dir', default='./results',
                        help='Output directory for results (default: ./results)')
    output_group.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output with debug information')
    output_group.add_argument('--no-color', action='store_true',
                        help='Disable colored output')
    output_group.add_argument('--json', action='store_true',
                        help='Output results as JSON to stdout')

    # GENERAL OPTIONS
    general_group = parser.add_argument_group('GENERAL OPTIONS', 'General fuzzing options')
    general_group.add_argument('-t', '--threads', type=int, default=10,
                        help='Number of concurrent threads (default: 10)')
    general_group.add_argument('--rate', type=int,
                        help='Request rate limit (requests per second)')
    general_group.add_argument('--maxtime', type=int,
                        help='Maximum execution time in seconds')
    general_group.add_argument('-c', '--colored', action='store_true', default=True,
                        help='Colored output (default: enabled)')
    general_group.add_argument('-s', '--silent', action='store_true',
                        help='Silent mode (only show results)')
    general_group.add_argument('-p', '--progress', action='store_true',
                        help='Show progress bar')
    general_group.add_argument('-V', '--version', action='store_true',
                        help='Show version information')

    # AI OPTIONS
    ai_group = parser.add_argument_group('AI OPTIONS', 'AI-powered selection and generation')
    ai_group.add_argument('--config-seclists',
                        help='Set SecLists installation path')
    ai_group.add_argument('--openai-key',
                        help='Set OpenAI API key for GPT generation')
    ai_group.add_argument('--ai-mode', default='smart', choices=['smart', 'broad', 'narrow'],
                        help='AI selection mode: smart, broad, narrow (default: smart)')
    ai_group.add_argument('--explain', action='store_true',
                        help='Explain why a wordlist was selected')

    # ADVANCED OPTIONS
    adv_group = parser.add_argument_group('ADVANCED OPTIONS', 'Advanced fuzzing options')
    adv_group.add_argument('--config',
                        help='Load configuration from file')
    adv_group.add_argument('--save-config',
                        help='Save current options to config file')
    adv_group.add_argument('--request',
                        help='HTTP request file (raw format)')
    adv_group.add_argument('--recursion', action='store_true',
                        help='Enable recursion (subdirectory fuzzing)')
    adv_group.add_argument('--recursion-depth', type=int, default=1,
                        help='Maximum recursion depth (default: 1)')
    adv_group.add_argument('--http2', action='store_true',
                        help='Use HTTP/2 protocol')

    args = parser.parse_args()
    
    # Handle custom help
    if args.help or (len(sys.argv) == 1):
        print_help_menu()
        sys.exit(0)
    
    if args.version:
        print("FuzzAI v1.0.0")
        sys.exit(0)
    
    return args

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
            logger.debug(f"SecLists configured in config: {cfg_path} (exists)")
            return True
        else:
            logger.debug(f"SecLists configured in config but path not found or not a directory: {cfg_raw}")

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
            logger.debug(f"Found SecLists via FUZZAI_SECLISTS: {env_path}")
            return True
        else:
            logger.debug(f"FUZZAI_SECLISTS set but path invalid: {env_raw}")

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
        logger.debug(f"Checking possible SecLists location: {p}")
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
                logger.debug(f"Non-interactive: auto-configured SecLists: {p_norm}")
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
                logger.debug("User chose not to configure the detected SecLists path.")
                # Continue scanning other possible locations
                continue

    # 4) Nothing found — offer interactive install
    logger.debug("SecLists not found in configured, env or common locations.")
    try:
        answer = input("📥 Would you like to install SecLists now? (y/n): ").strip().lower()
    except EOFError:
        logger.debug("Non-interactive environment, skipping installation prompt.")
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

    # Handle configuration-only commands
    if args.config_seclists or args.openai_key or args.save_config:
        logger = setup_logger(verbose=args.verbose, no_color=args.no_color)
        config = Config()
        
        if args.config_seclists:
            config.set_seclists_path(args.config_seclists)
            logger.success(f"SecLists path configured: {args.config_seclists}")
        
        if args.openai_key:
            config.set_openai_key(args.openai_key)
            logger.success("OpenAI API key configured")
        
        if args.save_config:
            config.save()
            logger.success(f"Configuration saved to {config.config_file}")
        
        return

    # If user only wants to set config or openai key, allow that without requiring -u
    if not args.url:
        print("Error: -u/--url is required for fuzzing")
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
                logger.debug(f"Configured SecLists path valid: {cfg_norm}")
            else:
                logger.debug(f"Config has SecLists path but directory missing: {cfg}")
        else:
            logger.debug("No SecLists path configured")
    except Exception as e:
        logger.debug(f"Could not validate SecLists path: {e}")

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

        # Show only the basename
        try:
            display_path = os.path.basename(wordlist_path)
        except Exception:
            display_path = wordlist_path
        # Only show the green wordlist line, not the info one
        # If subdomain mode, show info about subdomain fuzzing
        subdomain_mode = False
        if args.url:
            url = args.url
            parsed = url.split('FUZZ')
            if len(parsed) > 1:
                before = parsed[0]
                if before.endswith('://') or before.endswith('://www.'):
                    subdomain_mode = True
        if subdomain_mode:
            logger.info("Subdomain fuzzing detected")
        logger.success(f"Selected wordlist: {display_path} ({sum(1 for _ in open(wordlist_path))} words)")
        

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
            display_path = os.path.basename(wordlist_path)
        except Exception:
            display_path = wordlist_path
        logger.success(f"✓ Generated wordlist: {display_path}")
        if args.verbose:
            logger.debug(f"Full path: {wordlist_path}")

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

    # Process headers
    headers = {}
    if args.header:
        for header in args.header:
            if ':' in header:
                key, val = header.split(':', 1)
                headers[key.strip()] = val.strip()

    # Use POST data if provided
    post_data = args.data or args.data_ascii

    # Initialize and run fuzzer
    fuzzer = Fuzzer(
        url=args.url,
        wordlist_path=wordlist_path,
        threads=args.threads,
        timeout=args.timeout,
        delay=args.delay,
        response_filter=response_filter,
        output_file=args.output,
        verbose=args.verbose,
        method=args.method,
        headers=headers,
        data=post_data,
        insecure=args.insecure,
        follow_redirects=args.follow_redirect,
        proxy=args.proxy,
        explain=args.explain
    )

    try:
        fuzzer.run()
    except KeyboardInterrupt:
        logger.warning("\n Fuzzing interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
