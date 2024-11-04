
from bot import Bot
from bettor import Bettor, HttpBettor
from llm import Llm, MockLlm, GptLlm
from decision_maker import DecisionMaker, RandomDecisionMaker
from market_fetcher import MarketFetcher, MockMarketFetcher, HttpMarketFetcher
from search_handler import SearchHandler, MockSearchHandler, BingSearchHandler

import argparse
from typing import Union

SEARCH_TYPES = ["mock", "bing", "none"]
LLM_ARGS = {
        "mock": (MockLlm, ()),
        "gpt-4o": (GptLlm, ("gpt-4o",)),
        "gpt-4o-mini": (GptLlm, ("gpt-4o-mini",))
        }

# Set up argument parsing
def parse_args():
    parser = argparse.ArgumentParser(description="Run a language model with options for mock or OpenAI API usage.")

    # Define the flags
    parser.add_argument('--input_file', type=str, required=True,
            help='Path to the input file containing the prompt or data to process.')
    parser.add_argument('--output_file', type=str, required=True,
            help='Path to the output file where the result will be saved.')
    parser.add_argument('--mock_markets', action='store_true',
            help='Whether to use mock markets instead of the Manifold API.')
    parser.add_argument('--search_type', type=str, required=False,
            help=f'Which type of search to use. Valid search types: {", ".join(SEARCH_TYPES)}')
    parser.add_argument('--bet_type', type=str, required=False,
            help=f'The betting behavior - either real, dry_run, or none (no calling the Manifold API at all).')
    parser.add_argument('--llm', type=str, required=True,
            help=f'Flag to indicate which LLM to use. Valid LLMs: {", ".join(LLM_ARGS.keys())}')
    parser.add_argument('--openai_key_path', type=str, required=False,
            help='Path to a file containing the OpenAI API key.')
    parser.add_argument('--bing_key_path', type=str, required=False,
            help='Path to a file containing the Bing API key.')
    parser.add_argument('--manifold_key_path', type=str, required=True,
            help='Path to a file containing the Manifold API key.')

    return parser.parse_args()

def process_markets_file(input_file: str, output_file: str, bot: Bot, bettor: Union[Bettor, None], market_fetcher: MarketFetcher):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            market_url = line.split(' #')[0].strip()

            decision = bot.get_decision_for_market(market_url)
            choice = decision['choice']

            bet_str = f"{market_url}: {choice}"
            outfile.write(f"{bet_str} (reasoning: {decision['reasoning']})\n")

            print(bet_str)

            if bettor:
                market_id = market_fetcher.get_market_data(market_url)['id']
                bettor.bet(market_id, choice)

def get_bettor(args):
    if not args.bet_type or args.bet_type == "none":
        return None
    elif args.bet_type in ("dry_run", "real"):
        with open(args.manifold_key_path, 'r') as f:
            manifold_api_key = f.read().strip()
        dry_run = args.bet_type == "dry_run"
        return HttpBettor(manifold_api_key, dry_run=dry_run)
    else:
        raise ValueError(f"Unknown bet type {args.bet_type}")


def get_search_handler(args):
    if not args.search_type or args.search_type == "none":
        return None
    elif args.search_type == "mock":
        return MockSearchHandler()
    elif args.search_type == "bing":
        with open(args.bing_key_path, 'r') as f:
            bing_key = f.read().strip()
        return BingSearchHandler(bing_key)
    else:
        raise ValueError(f"Unknown search type {args.search_type}")


if __name__ == "__main__":
    args = parse_args()

    market_fetcher = MockMarketFetcher() if args.mock_markets else HttpMarketFetcher()

    bettor = get_bettor(args)

    # You could use the Llm class as an argument to your DecisionMaker.
    # Hardcoding to the RandomDecisionMaker for now.
    decision_maker = RandomDecisionMaker()

    search_handler = get_search_handler(args)

    bot = Bot(decision_maker, market_fetcher, search_handler)

    process_markets_file(args.input_file, args.output_file, bot, bettor, market_fetcher)
