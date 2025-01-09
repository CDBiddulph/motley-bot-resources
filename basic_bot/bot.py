import datetime
import json
import textwrap

from typing import List, Dict

from decision_maker import DecisionMaker
from llm import Llm
from market_fetcher import MarketFetcher
from search_handler import SearchHandler


def _comments_to_string_list(comments):
    return [f"{c['user']} ({c['time']}): {c['text']}" for c in comments]


class Bot:
    def __init__(self, decision_maker: DecisionMaker, market_fetcher: MarketFetcher, search_handler: SearchHandler, search_llm: Llm):
        self._decision_maker = decision_maker
        self._market_fetcher = market_fetcher
        self._search_handler = search_handler
        self._search_llm = search_llm

    # Note: this function is currently only used for generating search queries.
    def _get_market_string(self, market_data: Dict):
        comments = "\n".join(
            [f"- {c['user']} ({c['time']}): {c['text']}" for c in market_data['comments']])
        result = textwrap.dedent(f"""
                Title: {market_data['title']}
                Description: {market_data['description']}

                Current date: {market_data['current_date']}
                Close date: {market_data['close_date']}
                """)
        if comments:
            result += "\nComments on Manifold Markets:\n" + comments
        return result

    def _generate_search_query_prompt(self, market_data: Dict) -> str:
        prompt = f"""
Based on the following prediction market information, what is a single search engine query you would make to gather more relevant information for making a decision on how to bet?

{self._get_market_string(market_data)}

Please suggest one search query that would help in analyzing this market.
Write only the search query, nothing else.
"""
        return prompt

    def _get_llm_search_queries(self, prompt: str) -> List[str]:
        # Only return a single search query.
        return [self._search_llm.sample_text(prompt, max_tokens=32).strip()]

    def _generate_final_decision_prompt(self, market_data: Dict, search_results: Dict[str, List[str]]) -> str:
        question = market_data['title']
        description = market_data['description']
        today = market_data['current_date'].strftime("%Y-%m-%d")
        comments = "\n".join(
            [f"- {c['user']} ({c['time']}): {c['text']}" for c in market_data['comments']])

        formatted_search_results = ""
        if search_results:
            formatted_search_results = "\n".join(
                [f"- {snippet}" for snippets in search_results.values() for snippet in snippets])

        prompt = f"""
You are an advanced AI system which has been finetuned to provide calibrated probabilistic forecasts under uncertainty, with your performance evaluated according to the Brier score. When forecasting, do not treat 0.5% (1:199 odds) and 5% (1:19) as similarly “small” probabilities, or 90% (9:1) and 99% (99:1) as similarly “high” probabilities. As the odds show, they are markedly different, so output your probabilities accordingly. You will forecast the resolution of a question on the prediction market site Manifold Markets.

**Question:**  
{question}
 
**Description:**
{description}

**Today’s date:**  
{today}

**Market's closing date:**  
{market_data['close_date'].strftime("%Y-%m-%d")}

**Comments on Manifold Markets:**
<manifold_comments>
{comments}
</manifold_comments>

**Search results:**
<search_results>
{formatted_search_results}
</search_results>
 
**Recall the question you are forecasting:**  
{question}
 
### Instructions:

1. **Compress key factual information from the sources, as well as useful background information which may not be in the sources, into a list of core factual points to reference.**  
   Aim for information which is specific, relevant, and covers the core considerations you’ll use to make your forecast. For this step, do not draw any conclusions about how a fact will influence your answer or forecast. Place this section of your response in `<facts></facts>` tags.

2. **Provide a few reasons why the answer might be no.**  
   Rate the strength of each reason on a scale of 1-10. Use `<no></no>` tags.

3. **Provide a few reasons why the answer might be yes.**  
   Rate the strength of each reason on a scale of 1-10. Use `<yes></yes>` tags.

4. **Aggregate your considerations.**  
   Do not summarize or repeat previous points; instead, investigate how the competing factors and mechanisms interact and weigh against each other.  
   - Factorize your thinking across (exhaustive, mutually exclusive) cases if and only if it would be beneficial to your reasoning.  
   - Adjust for biases: You overestimate world conflict, drama, violence, and crises due to news’ negativity bias, which doesn’t necessarily represent overall trends or base rates. Similarly, you overestimate dramatic, shocking, or emotionally charged news due to news’ sensationalism bias.  
   - Consider reasons why the provided sources might be biased or exaggerated.  
   - Think like a superforecaster. Use `<thinking></thinking>` tags for this section of your response.

5. **Output an initial probability (prediction) as a single number between 0 and 1 given steps 1-4.**  
   Use `<tentative></tentative>` tags.

6. **Reflect on your answer, performing sanity checks and mentioning any additional knowledge or background information which may be relevant.**  
   - Check for over/underconfidence, improper treatment of conjunctive or disjunctive conditions (only if applicable), and other forecasting biases when reviewing your reasoning.  
   - Consider priors/base rates, and the extent to which case-specific information justifies the deviation between your tentative forecast and the prior.  
   - Aggregate all your previous reasoning and highlight key factors that inform your final forecast. Use `<thinking></thinking>` tags for this portion of your response.
   - Don't start this section with e.g. "my tentative answer was too low/high because..." You should only make a judgement *after* reflection is complete.

7. **Output your final prediction (a number between 0 and 1 with an asterisk at the beginning and end of the decimal) in `<answer></answer>` tags.
"""
        return prompt

    def _get_search_results_for_market(self, market_data: Dict) -> Dict[str, List[str]]:
        if not self._search_handler:
            return {}
        search_prompt = self._generate_search_query_prompt(market_data)
        search_queries = self._get_llm_search_queries(search_prompt)
        return {query: self._search_handler.search(query) for query in search_queries}

    def _format_search_results(self, search_results: Dict[str, List[str]]):
        # For now, we should only be making one search query.
        assert len(search_results) <= 1
        query, results = list(search_results.items())[0]
        results = "\n\n".join(results)
        return query, results

    def get_market_data(self, market_url: str) -> Dict:
        return self._market_fetcher.get_market_data(market_url)

    def get_decision_for_market(self, market_url: str):
        market_data = self.get_market_data(market_url)
        search_results = self._get_search_results_for_market(market_data)
        final_prompt = self._generate_final_decision_prompt(
            market_data, search_results)
        market_probability = market_data['probability']
        decision = self._decision_maker.make_decision(
            final_prompt, market_probability)
        decision["market_url"] = market_url
        decision["market_probability"] = market_probability
        decision["prompt"] = final_prompt
        decision["search_query"], decision["search_results"] = (
            self._format_search_results(search_results)
        )
        return decision, market_data
