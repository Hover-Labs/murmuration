import smartpy as sp

# A type recording the way an address voted.
# Params:
# - voteValue (nat): The Vote value
# - level (nat): The block level the vote was cast on.
# - votes (nat): The number of tokens voted with. 
VOTE_RECORD_TYPE = sp.TRecord(
  voteValue = sp.TNat,
  level = sp.TNat,
  votes = sp.TNat,
).layout(("voteValue", ("level", "votes")))