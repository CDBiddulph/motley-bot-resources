# Basic Bot

This directory contains the code for a bot that performs the following steps:

1. Reads a list of markets (in the same format that will be released on the day of the contest)
2. Fetches their info from Manifold
3. Turns each market into a prompt for an LLM (optionally incorporating search results from Bing)
4. Randomly selects between buying 1 mana in YES, buying 1 mana in NO, or doing nothing
5. Executes each trade

## Example command

Run the following command to place random bets for the list of markets stored at input_data/test_markets.txt.

```
python3 run.py \
  --input_file=input_data/test_markets.txt \
  --output_file=output_data/test.txt \
  --bet_type=dry_run \
  --manifold_key_path=../../my-manifold-key.txt
  --bing_key_path=../../my-bing-key.txt # Optional
```

``

`--input_file` is a newline-separated list of Manifold market URLs. `--output_file` will be written to with the decision and reasoning for each market.

The command uses the flag `--bet_type=dry_run` to make a call to the Manifold API that will fail if making the bet is not allowed, but otherwise doesn't do anything. You can change it to `--bet_type=real` to make actual bets with your Manifold API key, or `--bet_type=none` to skip the betting step entirely.

`--manifold_key_path` and `--bing_key_path` should be set to filepaths pointing to a text file containing the API key for Manifold or Bing.

## Setup

You will probably have to install some packages with pip before that command will work. DM me on Manifold or Discord if you're having trouble with setup.
