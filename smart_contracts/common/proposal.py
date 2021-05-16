import smartpy as sp

# Constants for Proposal based interactions.

# The type of a lambda that will be executed with a proposal.
PROPOSAL_LAMBDA_TYPE = sp.TLambda(sp.TUnit, sp.TList(sp.TOperation))

# The type of a proposal.
# Params:
# - title (string): The title of the proposal
# - descriptionLink (string): A link to the proposals description.
# - descriptionHash (string): A digest of the content at subscription link.
# - proposal (PROPOSAL_LAMBDA_TYPE): The code to execute.
PROPOSAL_TYPE = sp.TRecord(
  title = sp.TString,
  descriptionLink = sp.TString,
  descriptionHash = sp.TString,
  proposalLambda = PROPOSAL_LAMBDA_TYPE
).layout(("title", ("descriptionLink", ("descriptionHash", "proposalLambda"))))
