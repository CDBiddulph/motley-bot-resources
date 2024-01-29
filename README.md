# motley-bot-resources
Resources for the Motley Bot Challenge on Manifold Markets.

Challenge rules: https://manifold.markets/CDBiddulph/will-there-be-a-manifold-bot-that-m

## Directories
### select_markets
Contains the script that will be used to select markets for the contest, as well as example output files for each month up to January 1, 2025.

The script works as follows:
	1. Fetch all YES/NO markets that close between December 31 and January 7.
1. Randomly shuffle the list of markets. (Although they will get sorted in the next step, many markets will be equivalent in the sort order, so shuffling is still important.)
	1. Sort the markets based on the rules for "broadening the filter" as described in the challenge.
	1. Select the first 1000 markets in the sorted list.

	This script is subject to change, e.g. if I notice a bug or decide to make a minor change to the rules of the contest.
