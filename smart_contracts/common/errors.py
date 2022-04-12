import smartpy as sp

################################################################
################################################################
# Errors
################################################################
################################################################

# There is already a poll underway.
ERROR_POLL_UNDERWAY = "POLL_UNDERWAY"

# There is not a poll available.
ERROR_NO_POLL = "NO_POLL"

# There is already a item in the timelock.
ERROR_ITEM_IN_TIMELOCK = "ITEM_IN_TIMELOCK"

# There is no item in the timelock.
ERROR_NO_ITEM_IN_TIMELOCK = "NO_ITEM_IN_TIMELOCK"

# Voting is finished
ERROR_VOTING_FINISHED = "VOTING_FINISHED"

# Voting is not finished
ERROR_VOTING_NOT_FINISHED = "VOTING_NOT_FINISHED"

# The address has already voted.
ERROR_ALREADY_VOTED = "ALREADY_VOTED"

# The given vote value was invalid.
ERROR_BAD_VOTE_VALUE = "BAD_VOTE_VALUE"

# The entry point may only be called by the proposal's author.
ERROR_NOT_AUTHOR = "NOT_AUTHOR"

# The timelock can not be executed at this time.
ERROR_TOO_SOON = "TOO_SOON"

# This method may only be called by the dao.
ERROR_NOT_DAO = "NOT_DAO"

# The contract was not in the expected state.
ERROR_BAD_STATE = "BAD_STATE"

# An unknown error occurred.
ERROR_UNKNOWN = "UNKNOWN"

# The sender was not the token contract.
ERROR_NOT_TOKEN_CONTRACT = "NOT_TOKEN_CONTRACT"

# The operation requested too many tokens from the faucet
ERROR_TOO_MANY_TOKENS = "TOO_MANY_TOKENS"

# The requested block level hasn't occured.
ERROR_BLOCK_LEVEL_TOO_SOON = "BLOCK_LEVEL_TOO_SOON"

# The transaction tried to spend more tokens than were available
ERROR_LOW_BALANCE = "LOW_BALANCE"

# The transaction was not allowed
ERROR_NOT_ALLOWED = "NOT_ALLOWED"

# The system was paused
ERROR_PAUSED = "PAUSED"

# The allowance change was unsafe. Please reset it to zero first.
ERROR_UNSAFE_ALLOWANCE_CHANGE = "UNSAFE_ALLOWANCE_CHANGE"

# The operation must be completed via the withdraw entrypoint.
ERROR_USE_WITHDRAW = "USE_WITHDRAW_INSTEAD"

# The sender must be the governor
ERROR_NOT_GOVERNOR = "NOT_GOVERNOR"

# The sender must be the token administrator
ERROR_NOT_ADMINISTRATOR = "NOT_ADMINISTRATOR"

# The sender must be the owner
ERROR_NOT_OWNER = "NOT_OWNER"

# The requested operation could not be completed because not enough value is vested
ERROR_NOT_VESTED = "NOT_VESTED"

# A given parameter was an unacceptable value
ERROR_BAD_DAO_PARAM = "ERROR_BAD_DAO_PARAM"
