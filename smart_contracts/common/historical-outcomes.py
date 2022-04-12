import smartpy as sp

Poll = sp.io.import_script_from_url("file:common/poll.py")

# A historical result of a vote.
# Params:
# - outcome (nat): The outcome of the poll
# - poll (Poll.POLL_TYPE): The poll and the results.
HISTORICAL_OUTCOME_TYPE = sp.TRecord(
  outcome = sp.TNat,
  poll = Poll.POLL_TYPE
).layout(("outcome", "poll"))