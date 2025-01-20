import argparse
import dataclasses
import pytz
import random
import requests
import time

# from collections.abc import Collection
from datetime import datetime, timedelta
from tqdm import tqdm
from typing import Tuple, Sequence, Collection, Optional

PAGE_LENGTH = 1000

@dataclasses.dataclass
class FetchRequest:
    offset: int
    limit: int

def generate_request_data(n: int, start_offset: int) -> Sequence[FetchRequest]:
    # Not supporting starting in the middle of a page.
    assert start_offset % PAGE_LENGTH == 0

    full_calls = n // PAGE_LENGTH
    data = [FetchRequest(offset=i*PAGE_LENGTH + start_offset, limit=PAGE_LENGTH) for i in range(full_calls)]

    remaining_markets = n % PAGE_LENGTH
    if remaining_markets:
        data.append(FetchRequest(offset=full_calls*PAGE_LENGTH + start_offset, limit=remaining_markets))

    return data

def attempt_get_json(url: str, num_retries: int = 12, fixed_wait: int = 5):
    exception = None
    assert num_retries > 0
    for retry in range(num_retries):
        if retry > 0:
            time.sleep(fixed_wait)
            print("Retrying...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {retry}/{num_retries} failed for {url}")
            exception = e
    # It should be impossible for exception to be None
    raise exception

def get_fetch_markets_response(request_data: FetchRequest):
    assert request_data.limit <= PAGE_LENGTH
    url = f"https://api.manifold.markets/v0/search-markets?term=&limit={request_data.limit}&offset={request_data.offset}&filter=open&sort=close-date&contractType=BINARY"
    return attempt_get_json(url)

def str_to_datetime(datestring: str):
    # December 31, 2024 would be represented as 2024-12-31.
    time_format = "%Y-%m-%d"
    # Use the default timezone of UTC.
    return datetime.strptime(datestring, time_format)

def get_time_range(center_day: str, days_before: int, days_after: int):
    center_time = str_to_datetime(center_day)
    start_time = center_time - timedelta(days=days_before)
    # Add an extra day and subtract one second, so that we get the markets
    # that close *during* the last day as well.
    end_time = center_time + timedelta(days=days_after+1) - timedelta(seconds=1)

    return start_time, end_time

def get_datetime(timestamp: int):
    # Use the default timezone of UTC.
    return datetime.utcfromtimestamp(timestamp / 1000.0)

def get_timestamp(dt):
    return dt.timestamp() * 1000


def get_start_offset_for_time(min_time):
    offset = 0
    while True:
        market = get_fetch_markets_response(FetchRequest(offset=offset, limit=1))[0]
        if market["closeTime"] >= get_timestamp(min_time):
            return max(0, offset - PAGE_LENGTH)
        offset += PAGE_LENGTH

@dataclasses.dataclass
class Market:
    market_id: str
    url: str
    close_time: datetime
    num_bettors: int
    _tags: Optional[Collection[str]] = None

    @property
    def tags(self):
        """Lazily calculate tags."""
        if self._tags is None:
            self._tags = get_market_tags(self.market_id)
        return self._tags

    def has_tags(self):
        """Return True if _tags is already calculated."""
        return self._tags is not None

    def __hash__(self):
        # market_id should be sufficient to identify the Market.
        return hash(self.market_id)

def get_market_from_json(market_json):
    market = Market(
            market_id=market_json["id"],
            url=market_json["url"],
            close_time=get_datetime(market_json["closeTime"]),
            num_bettors=market_json["uniqueBettorCount"],
            )
    return market

def get_markets_in_time_range(min_close_time: datetime, max_close_time: datetime):
    offset = get_start_offset_for_time(min_close_time)
    markets = []
    done = False
    while not done:
        for market_json in get_fetch_markets_response(FetchRequest(offset=offset, limit=PAGE_LENGTH)):
            close_time = market_json["closeTime"]
            if close_time > get_timestamp(max_close_time):
                done = True
                break
            elif close_time < get_timestamp(min_close_time):
                if markets:
                    raise ValueError("A market before min close time appeared after the first market had already been added:\n" + str(market))
            else:
                markets.append(get_market_from_json(market_json))
        offset += PAGE_LENGTH
    # Deduplicate markets and return.
    return list({market.market_id: market for market in markets}.values())

@dataclasses.dataclass
class FilterConfig:
    last_free_day: str
    bettor_range: Tuple[int, int]
    bad_tags: Sequence[str]

    def __hash__(self):
        return hash((self.last_free_day, tuple(self.bettor_range), tuple(self.bad_tags)))

def days_since(dt, since_datestring: str) -> int:
    since_datetime = str_to_datetime(since_datestring)
    return (dt - since_datetime).days

def get_market_tags(market_id: str) -> Collection[str]:
    url = "https://api.manifold.markets/v0/market/" + market_id
    market_json = attempt_get_json(url)
    return set(market_json["groupSlugs"]) if "groupSlugs" in market_json else {}

# Returns a tuple with elements representing filter criteria in order of their priority.
# This may take a while because market.tags makes a call to the API.
def get_market_sort_key(market: Market, filter_cfg: FilterConfig):

    key = []
    # Add a penalty for each bad tag, in order of how important they are to avoid.
    # Since market.tags is lazily evaluated, the tags won't be fetched if
    # the list of bad tags is empty.
    for tag in reversed(filter_cfg.bad_tags):
        key.append(int(tag in market.tags))
    # Add a penalty for being below the bettor range, then for being above the bettor range.
    key.append(max(0, filter_cfg.bettor_range[0] - market.num_bettors))
    key.append(max(0, market.num_bettors - filter_cfg.bettor_range[1]))
    # Add a penalty for the close time being past the "last free day."
    key.append(max(0, days_since(market.close_time, filter_cfg.last_free_day)))
    # Convert to a tuple so we can use it as a key.
    return tuple(key)

def filter_markets(markets, max_markets: int, filter_cfg: FilterConfig):
    random.shuffle(markets)
    markets_with_sort_keys = [(get_market_sort_key(m, filter_cfg), m) for m in tqdm(markets, desc="Sorting markets")]
    markets_with_sort_keys.sort(key=lambda m: m[0])
    return [m for _, m in markets_with_sort_keys][:max_markets]

def get_market_comment(market: Market, bad_tags: Collection[str]) -> str:
    tags_str = ""
    if market.has_tags():
        # Filter the list of tags to only bad tags, in order of priority.
        tags = [t for t in reversed(bad_tags) if t in market.tags]
        tags_str = f" Tags: {tags}" if tags else ""
    return f"Closes {market.close_time}. {market.num_bettors} bettors.{tags_str}"

def get_datestr(dt) -> str:
    return dt.strftime('%Y-%m-%d')

def write_markets_to_file(markets: Sequence[Market], outfile: str, min_time: datetime, soft_max_datestr: str, hard_max_time: datetime, bad_tags: Collection[str]):
    with open(outfile, 'w') as f:
        f.write(f"# {len(markets)} markets selected on {get_datestr(datetime.now())}.\n")
        f.write(f"# Close dates from {get_datestr(min_time)} to {soft_max_datestr} (or possibly up to {get_datestr(hard_max_time)}).\n")
        for market in markets:
            market_str = market.url + "\t\t# " + get_market_comment(market, bad_tags)
            f.write(market_str + '\n')

def main(max_markets: int, last_free_day: str, bettor_range: Tuple[int, int], bad_tags: Sequence[str], outfile: str):
    # If last_free_day is January 1, we should fetch markets with close dates
    # in the range from December 31 to January 7 (including markets that close on January 7).
    min_close_time, max_close_time = get_time_range(last_free_day, days_before=1, days_after=6)
    print(f"Fetching markets that close between {min_close_time} and {max_close_time}.")
    markets = get_markets_in_time_range(min_close_time, max_close_time)
    print(f"Fetched {len(markets)} markets.")

    filter_cfg = FilterConfig(
            last_free_day = last_free_day,
            bettor_range = bettor_range,
            bad_tags = bad_tags
            )
    markets = filter_markets(markets, max_markets=max_markets, filter_cfg=filter_cfg)
    print(f"Filtered to {len(markets)} markets (of {max_markets} maximum).")

    write_markets_to_file(markets, outfile, min_close_time, last_free_day, max_close_time, filter_cfg.bad_tags)
    print(f"Wrote markets to {outfile}")

def parse_args():
    parser = argparse.ArgumentParser(description='Selects markets for the Motley Bot Challenge.')

    parser.add_argument('--max_markets', type=int, default=1000, help="The maximum number of markets to return.")
    parser.add_argument('--last_free_day', type=str, default="2025-01-01", help="The last day before markets start getting a \"penalty\" in the sort order.")
    parser.add_argument('--bettor_range', nargs='+', type=int, default=[10, 20], help="The (inclusive) range of the number of bettors before getting a penalty.")
    parser.add_argument('--bad_tags', nargs='+', type=str, default=[
        "personal",
        "personal-goals",
        "fun",
        "selfresolving",
        "free-money",
        "nonpredictive-profits",
        "nonpredictive",
        "unsubsidized"
        ], help='List of bad tags')
    parser.add_argument('--ignore_tags', action='store_true', help="If true, ignore the tags in bad_tags. This allows the script to run much faster since we don't have to fetch the tags for each individual market.")
    parser.add_argument('--outfile', type=str, required=True, help="The file to write a list of markets to.")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    bad_tags = [] if args.ignore_tags else args.bad_tags

    main(args.max_markets, args.last_free_day, args.bettor_range, bad_tags, args.outfile)

