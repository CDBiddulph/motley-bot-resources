from bot import Bot
from bettor import Bettor, HttpBettor
from llm import Llm, MockLlm, ClaudeLlm
from decision_maker import DecisionMaker, RandomDecisionMaker, LlmDecisionMaker
from market_fetcher import MarketFetcher, MockMarketFetcher, HttpMarketFetcher
from search_handler import SearchHandler, MockSearchHandler, BingSearchHandler

import argparse
import json
import re
import os
from typing import Union

SEARCH_TYPES = ["mock", "bing", "none"]
LLM_ARGS = {
    "mock": (MockLlm, ()),
    "claude": (ClaudeLlm, ("claude-3-5-sonnet-latest",)),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a basic Manifold bot for the Motley Bot Challenge.")

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
    parser.add_argument('--anthropic_key_path', type=str, required=False,
                        help='Path to a file containing the Anthropic API key.')
    parser.add_argument('--bing_key_path', type=str, required=False,
                        help='Path to a file containing the Bing API key.')
    parser.add_argument('--manifold_key_path', type=str, required=False,
                        help='Path to a file containing the Manifold API key.')
    parser.add_argument('--prediction_model', type=str, default="claude-3-5-sonnet-latest",
                        help='The model name of the LLM to be used to write search queries.')
    parser.add_argument('--search_model', type=str, default="claude-3-5-haiku-latest",
                        help='The model name of the LLM to be used to write search queries.')
    return parser.parse_args()


def process_markets_file(
        input_file: str,
        output_file: str,
        bot: Bot,
        bettor: Union[Bettor, None],
        market_fetcher: MarketFetcher,
):
    # Collect already processed markets if output_file exists.
    # This lets you use data from a past run. There are two reasons you might
    # want to do this:
    # - If the script fails in the middle of its run, this lets you recover
    #   your progress.
    # - You can separate the process of gathering the predictions and actually
    #   executing them. You can do this by populating output_file completely
    #   with --bet_type=none, then rerunning the script with the same output_file
    #   and --bet_type=real.
    processed_markets = set()
    if os.path.exists(output_file):
        with open(output_file, 'r') as outfile:
            for line in outfile:
                decision = json.loads(line)
                if 'market_url' in decision:
                    processed_markets.add(decision['market_url'])

    with open(input_file, 'r') as infile, open(output_file, 'a') as outfile:
        market_i = 0
        for line in infile:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            market_i += 1
            market_url = re.split(r'[ \t]+#', line)[0].strip()
            if market_url in processed_markets:
                print(f"{market_i}. Skipping already processed market: {market_url}")
                continue

            decision, market_data = bot.get_decision_for_market(market_url)
            outfile.write(json.dumps(decision) + "\n")

            print(
                f"{market_i}. Market: {market_url}, Decision: {decision['decision']}")

            # Prevents duplication if the same market appears twice (shouldn't happen, but it does).
            processed_markets.add(market_url)

    if not bettor:
        return
    bet_markets = set()
    with open(output_file, 'r') as outfile:
        market_i = 0
        for line in outfile:
            if not line:
                continue
            decision = json.loads(line)
            market_url = decision['market_url']

            if market_url in bet_markets:
                print(f"Skipping already bet market: {market_url}")
                continue
            bet_markets.add(market_url)
            market_i += 1

            market_data = bot.get_market_data(market_url)
            market_id = market_data['id']
            decision_str = decision['decision']
            print(f"{market_i}. Bet {decision_str} on {market_url}...")
            bettor.bet(market_id, decision_str)
            print(f"{market_i}. Bet {decision_str} on {market_url}")


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

    if args.llm == "mock":
        prediction_llm = MockLlm()
    elif args.llm == "claude":
        with open(args.anthropic_key_path, 'r') as f:
            anthropic_api_key = f.read().strip()
        prediction_llm = ClaudeLlm(
            anthropic_api_key, model=args.prediction_model)
    else:
        raise ValueError(f"Unknown LLM: {args.llm}")

    if args.search_type == "mock":
        search_llm = MockLlm()
    elif args.search_type == "bing":
        with open(args.anthropic_key_path, 'r') as f:
            anthropic_api_key = f.read().strip()
        search_llm = ClaudeLlm(anthropic_api_key, model=args.search_model)
    else:
        search_llm = None

    decision_maker = LlmDecisionMaker(prediction_llm)

    search_handler = get_search_handler(args)

    bot = Bot(decision_maker, market_fetcher, search_handler, search_llm)

    process_markets_file(args.input_file, args.output_file,
                         bot, bettor, market_fetcher)
