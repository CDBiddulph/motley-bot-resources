import datetime
import json
import random
import requests
import textwrap

from typing import List, Dict, Tuple

from decision_maker import DecisionMaker, RandomDecisionMaker
from llm import Llm
from market_fetcher import MarketFetcher
from search_handler import SearchHandler


MOCK_SEARCH_RESULTS = [
        "Recent studies show exponential growth in AI capabilities, with some experts predicting human-level AI by 2029.",
        "While progress in AI has been rapid, many researchers caution that general intelligence is still far off.",
        "SpaceX has successfully tested its Starship prototype, but Mars missions face numerous additional challenges.",
        ]

def _comments_to_string_list(comments):
    return [f"{c['user']} ({c['time']}): {c['text']}" for c in comments]

def _format_string_list(name, string_list, indent=0):
    if not string_list:
        return ""
    indent_str = "  " * indent
    bullets_str = '\n'.join(f'{indent_str}- ' + s for s in string_list)
    result = textwrap.dedent("""
    %s:
    %s
    """) % (name, bullets_str)
    return result

def _format_search_results(search_results):
    search_result_strs = []
    for query, snippets in search_results.items():
        search_result_strs.append(_format_string_list(query, snippets, indent=1).strip())
    return _format_string_list("Search results", search_result_strs)

class Bot:
    def __init__(self, decision_maker: DecisionMaker, market_fetcher: MarketFetcher, search_handler: SearchHandler):
        self._decision_maker = decision_maker
        self._market_fetcher = market_fetcher
        self._search_handler = search_handler

    def _get_market_string(self, market_data: Dict):
        comments = _format_string_list("Comments", _comments_to_string_list(market_data['comments']))
        result = textwrap.dedent(f"""
                Title: {market_data['title']}
                Creator: {market_data['creator']}
                Description: {market_data['description']}

                Current probability: {market_data['probability']}
                Current date: {market_data['current_date']}
                Close date: {market_data['close_date']}
                """)
        if comments:
            result += "\n" + comments
        return result

    def _generate_search_query_prompt(self, market_data: Dict) -> str:
        prompt = textwrap.dedent("""
        Based on the following prediction market information, what search engine queries would you make to gather more relevant information for making a decision on how to bet?

        %s

        Please suggest up to 3 search queries that would help in analyzing this market.
        Respond in JSON format like this:
            {"search_queries": ["query1", "query2", "query3"]}
        """) % (self._get_market_string(market_data),)
        return prompt

    def _get_llm_search_queries(self, prompt: str) -> List[str]:
        # TODO: implement a non-mock version of this, using an LLM.
        title_str = "Title: "
        title_start = prompt.index(title_str) + len(title_str)
        title_end = prompt.find('\n', title_start)
        title = prompt[title_start:title_end]
        result = ["Recent developments in " + title,
                "Expert opinions on " + title,
                "Challenges in " + title,
                ]
        return result

    def _generate_final_decision_prompt(self, market_data: Dict, search_results: List[str]) -> str:
        prompt = textwrap.dedent("""
        Based on the following prediction market information and search results (if any), what action would you recommend?

        %s
        %s

        Choose from: BUY_YES, BUY_NO, or DO_NOTHING.

        Respond in JSON format like this:
        {"reasoning": "YOUR REASONING", "choice": "YOUR_CHOICE"}
        """) % (self._get_market_string(market_data), _format_search_results(search_results))
        return prompt


    def _get_search_results_for_market(self, market_data: Dict) -> Dict[str, List[str]]:
        if not self._search_handler:
            return {}
        search_prompt = self._generate_search_query_prompt(market_data)
        search_queries = self._get_llm_search_queries(search_prompt)
        return {query: self._search_handler.search(query) for query in search_queries}

    def get_decision_for_market(self, market_url: str) -> Dict:
        market_data = self._market_fetcher.get_market_data(market_url)
        search_results = self._get_search_results_for_market(market_data)
        final_prompt = self._generate_final_decision_prompt(market_data, search_results)
        return self._decision_maker.make_decision(final_prompt)

