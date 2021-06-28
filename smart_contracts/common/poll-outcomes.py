################################################################
################################################################
# Poll Outcomes
################################################################
################################################################

POLL_OUTCOME_FAILED = 0       # Did not pass voting
POLL_OUTCOME_IN_TIMELOCK = 1  # Passed voting, is in timelock
POLL_OUTCOME_EXECUTED = 2     # Passed voting, executed in timelock
POLL_OUTCOME_CANCELLED = 3    # Passed voting, but cancelled from timelock
