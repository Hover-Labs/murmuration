import smartpy as sp

# This file contains addresses for tests which are named and ensure uniqueness across the test suite.

# The address which acts as the Token Admin
TOKEN_ADMIN_ADDRESS = sp.address("tz1abmz7jiCV2GH2u81LRrGgAFFgvQgiDiaf")

# An address that receives tokens.
TOKEN_RECIPIENT = sp.address("tz1c461F8GirBvq5DpFftPoPyCcPR7HQM6gm")

# The address which acts as the token contract.
TOKEN_CONTRACT_ADDRESS = sp.address("tz1P2Po7YM526ughEsRbY4oR9zaUPDZjxFrb")

# The address wich acts as a Community Fund
COMMUNITY_FUND_ADDRESS = sp.address("tz1UUgPwikRHW1mEyVZfGYy6QaxrY6Y7WaG5")

# An address which represents a voter in the DAO.
VOTER_ADDRESS = sp.address("tz1TDSmoZXwVevLTEvKCTHWpomG76oC9S2fJ")

# An address which acts as a Governor.
GOVERNOR_ADDRESS = sp.address("tz1VmiY38m3y95HqQLjMwqnMS7sdMfGomzKi")

# An address will be rotated to
ROTATED_ADDRESS = sp.address("tz1W5VkdB5s7ENMESVBtwyt9kyvLqPcUczRT")

# The owner of a vesting contract.
OWNER_ADDRESS = sp.address("tz1aRoaRhSpRYvFdyvgWLL6TGyRoGF51wDjM")

# The dao address.
DAO_ADDRESS = sp.address("tz1WpeqFaBG9Jm73Dmgqamy8eF8NWLz9JCoY")

# An series of named addresses with no particular role.
# These are used for token transfer tests.
ALICE_ADDRESS = sp.address("tz1LLNkQK4UQV6QcFShiXJ2vT2ELw449MzAA")
BOB_ADDRESS = sp.address("tz1UMCB2AHSTwG7YcGNr31CqYCtGN873royv")
CHARLIE_ADDRESS =sp.address("tz1R6Ej25VSerE3MkSoEEeBjKHCDTFbpKuSX")

# An address which is never used. This is a `null` value for addresses.
NULL_ADDRESS = sp.address("tz1bTpviNnyx2PXsNmGpCQTMQsGoYordkUoA")
