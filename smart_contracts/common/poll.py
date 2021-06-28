import smartpy as sp

Proposal = sp.import_script_from_url("file:common/proposal.py")
QuorumCap = sp.import_script_from_url("file:common/quorum-cap.py")
VoteRecord = sp.import_script_from_url("file:common/vote-record.py")

# A poll for a proposal.
# Params:
# - id (nat): An automatically assigned identifier for the poll.
# - proposal (Proposal.PROPOSAL_TYPE): The proposal
# - votingStart (nat): The first block of voting.
# - votingEnd (nat): The last block of voting.
# - yayVotes (nat): The number of yay votes.
# - nayVotes (nat): The number of nay votes.
# - abstainVotes (nat): The number of abstain votes.
# - totalVotes (nat): The total number of votes.
# - voters (set<nat>): The addresses which have voted.
# - author (address): The author of the proposal.
# - escrowAmount (nat): The amount of tokens escrowed for the proposal.
# - quorum (nat): The quorum the poll needs to achieve. 
# - quorumCap (nat): The quorum caps of the proposal.
POLL_TYPE = sp.TRecord(
  id = sp.TNat,
  proposal = Proposal.PROPOSAL_TYPE,
  votingStartBlock = sp.TNat,
  votingEndBlock = sp.TNat,
  yayVotes = sp.TNat,
  nayVotes = sp.TNat,
  abstainVotes = sp.TNat,
  totalVotes = sp.TNat,
  voters = sp.TMap(sp.TAddress, VoteRecord.VOTE_RECORD_TYPE),
  author = sp.TAddress,
  escrowAmount = sp.TNat,
  quorum = sp.TNat,
  quorumCap = QuorumCap.QUORUM_CAP_TYPE
).layout(("id", ("proposal", ("votingStartBlock", ("votingEndBlock", ("yayVotes", ("nayVotes", ("abstainVotes", ("totalVotes", ("voters", ("author", ("escrowAmount", ("quorum", "quorumCap")))))))))))))
