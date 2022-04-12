import smartpy as sp

Addresses = sp.io.import_script_from_url("file:test-helpers/addresses.py")
Errors = sp.io.import_script_from_url("file:common/errors.py")
HistoricalOutcomes = sp.io.import_script_from_url("file:common/historical-outcomes.py")
Poll = sp.io.import_script_from_url("file:common/poll.py")
PollOutcomes = sp.io.import_script_from_url("file:common/poll-outcomes.py")
Proposal = sp.io.import_script_from_url("file:common/proposal.py")
QuorumCap = sp.io.import_script_from_url("file:common/quorum-cap.py")
VoteRecord = sp.io.import_script_from_url("file:common/vote-record.py")
VoteValue = sp.io.import_script_from_url("file:common/vote-value.py")

################################################################
################################################################
# Constants
################################################################
################################################################

# Scale is the precision with which numbers are measured.
# For instance, a scale of 100 means the number 1.23 is represented
# as 123.
SCALE = 100 

################################################################
################################################################
# State Machine
################################################################
################################################################

STATE_MACHINE_IDLE = 0
STATE_MACHINE_WAITING_FOR_BALANCE = 1

################################################################
################################################################
# Types
################################################################
################################################################

# A item in the timelock
# Params:
# - id (nat): An automatically assigned identifier for the timelock item. This is the same ID that is used in polls.
# - proposal (Proposal.PROPOSAL_TYPE): The proposal
# - endBlock (nat): The block where the item can be executed.
# - cancelBlock (nat): The block where the item can be cancelled.
# - author (address): The author of the proposal.
TIMELOCK_ITEM_TYPE = sp.TRecord(
  id = sp.TNat,
  proposal = Proposal.PROPOSAL_TYPE,
  endBlock = sp.TNat,
  cancelBlock = sp.TNat,
  author = sp.TAddress
).layout(("id", ("proposal", ("endBlock", ("cancelBlock", "author")))))

# Governance parameters.
# Params:
# - escrowAmount (nat): The number of tokens to escrow when a proposal is submitted.
# - delayBlocks (nat): The number of blocks to delay voting once a proposal is submitted.
# - voteLengthBlocks (nat): The number of blocks a vote takes.
# - minYayVotesPercentForEscrowReturn (nat): The minimum percent of yay votes needed to receive an escrow back. Represented with scale = 2. Ex. 20 = .20 = 20%.
# - blocksInTimelockForExecution (nat): The number of blocks a timelock lasts for.
# - blocksInTimelockForCancellation (nat): The number of blocks a proposal can be in a timelock before it becomes cancellable.
# - percentageForSuperMajority (nat): The percentage of votes needed for a super majority. Represented with scale = 2. Ex. 80 = .80 = 80%.
# - quorumCaps (Record<nat, nat>): The upper and lower bounds for quorum.
GOVERNANCE_PARAMETERS_TYPE = sp.TRecord(
  escrowAmount = sp.TNat,
  voteDelayBlocks = sp.TNat,
  voteLengthBlocks = sp.TNat,
  minYayVotesPercentForEscrowReturn = sp.TNat,
  blocksInTimelockForExecution = sp.TNat,
  blocksInTimelockForCancellation = sp.TNat,
  percentageForSuperMajority = sp.TNat,
  quorumCap = QuorumCap.QUORUM_CAP_TYPE
).layout(
  (
    "escrowAmount", 
    (
      "voteDelayBlocks", 
      (
        "voteLengthBlocks", 
        (
          "minYayVotesPercentForEscrowReturn", 
          (
            "blocksInTimelockForExecution", 
            (
              "blocksInTimelockForCancellation",
              (
                "percentageForSuperMajority",
                "quorumCap"
              )
            )
          )
        )
      )
    )
  )
)

# A voting state.
# Params:
# - voteValue (nat): The value of the vote.
# - address (address): The address casting the vote.
# - level (nat): The block level data was requested at.
VOTING_STATE = sp.TRecord(
  voteValue = sp.TNat,
  address = sp.TAddress,
  level = sp.TNat
).layout(("voteValue", ("address", "level")))

################################################################
# Contract
################################################################

class DaoContract(sp.Contract):
  def __init__(
    self, 
    governanceParameters = sp.record(
      escrowAmount = sp.nat(100),
      voteDelayBlocks = sp.nat(1),
      voteLengthBlocks = sp.nat(180),
      # Minimum yes vote percentage to have the escrow returned. This number
      # is represented with scale = 2, ex. 20 = .20 = 20%.      
      minYayVotesPercentForEscrowReturn = sp.nat(20), # 20% 
      blocksInTimelockForExecution = sp.nat(10),
      blocksInTimelockForCancellation = sp.nat(15),
      # The percentage needed for a super majority. This number is represented
      # with scale = 2, ex. 80 = .80 = 80%
      percentageForSuperMajority = sp.nat(80),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(2)),
    ),
    poll = sp.none,
    timelockItem = sp.none,
    tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
    quorum = sp.nat(100),
    communityFundAddress = Addresses.COMMUNITY_FUND_ADDRESS,
    state = STATE_MACHINE_IDLE,
    votingState = sp.none,
    outcomes = sp.big_map(l = {}, tkey = sp.TNat, tvalue = HistoricalOutcomes.HISTORICAL_OUTCOME_TYPE),
  ):
    metadata_data = sp.utils.bytes_of_string('{ "name": "Kolibri Governance DAO", "authors": ["Hover Labs <hello@hover.engineering>"], "homepage":  "https://kolibri.finance" }')

    metadata = sp.big_map(
      l = {
        "": sp.bytes('0x74657a6f732d73746f726167653a64617461'), # "tezos-storage:data"
        "data": metadata_data
      },
      tkey = sp.TString,
      tvalue = sp.TBytes            
    )

    self.init_type(
      sp.TRecord(
        tokenContractAddress = sp.TAddress,
        communityFundAddress = sp.TAddress,
        governanceParameters = GOVERNANCE_PARAMETERS_TYPE,
        quorum = sp.TNat,
        poll = sp.TOption(Poll.POLL_TYPE),
        timelockItem = sp.TOption(TIMELOCK_ITEM_TYPE),
        nextProposalId = sp.TNat,
        state = sp.TNat,
        votingState = sp.TOption(VOTING_STATE),
        metadata = sp.TBigMap(sp.TString, sp.TBytes),
        outcomes = sp.TBigMap(sp.TNat, HistoricalOutcomes.HISTORICAL_OUTCOME_TYPE)
      )
    )

    self.init(
      # The address of the governance token contract.
      tokenContractAddress = tokenContractAddress,

      # The address of the community fund. 
      communityFundAddress = communityFundAddress,
      # Parameters this DAO uses to govern.
      governanceParameters = governanceParameters,
      # The quorum.
      quorum = quorum,
      # The poll which is underway.
      poll = poll,
      # The item in the timelock.
      timelockItem = timelockItem,

      # Internal state
      nextProposalId = sp.nat(0),
      outcomes = outcomes,

      # State machine
      state = state,
      votingState = votingState,

      # Contract metadata.
      metadata = metadata,
    )

  ################################################################
  # Proposal Management
  ################################################################

  # Add a governance proposal.
  # This method will escrow governance tokens.
  @sp.entry_point
  def propose(self, proposal):
    sp.set_type(proposal, Proposal.PROPOSAL_TYPE)

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Verify a poll is not under vote.
    sp.verify(~self.data.poll.is_some(), Errors.ERROR_POLL_UNDERWAY)

    # Escrow tokens.
    tokenContractHandle = sp.contract(
      sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
      self.data.tokenContractAddress,
      "transfer"
    ).open_some()
    tokenContractArg = sp.record(
      from_ = sp.sender, 
      to_ = sp.self_address, 
      value = self.data.governanceParameters.escrowAmount
    )
    sp.transfer(tokenContractArg, sp.mutez(0), tokenContractHandle)

    # Create a new contract under vote.
    startBlock = sp.level + self.data.governanceParameters.voteDelayBlocks
    endBlock = startBlock + self.data.governanceParameters.voteLengthBlocks
    self.data.poll = sp.some(
      sp.record(
        id = self.data.nextProposalId,
        proposal = proposal,
        votingStartBlock = startBlock,
        votingEndBlock = endBlock,
        yayVotes = sp.nat(0),
        nayVotes = sp.nat(0),
        abstainVotes = sp.nat(0),
        totalVotes = sp.nat(0),
        voters = sp.map(l = {}, tkey = sp.TAddress, tvalue = VoteRecord.VOTE_RECORD_TYPE),
        author = sp.sender,
        escrowAmount = self.data.governanceParameters.escrowAmount,
        quorum = self.data.quorum,
        quorumCap = self.data.governanceParameters.quorumCap
      )
    )

    self.data.nextProposalId = self.data.nextProposalId + 1

  # End voting for a poll.
  @sp.entry_point
  def endVoting(self, unit):
    sp.set_type(unit, sp.TUnit)

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Verify a poll is underway.
    sp.verify(self.data.poll.is_some(), Errors.ERROR_NO_POLL)

    # Verify the timelock is empty.
    sp.verify(~self.data.timelockItem.is_some(), Errors.ERROR_ITEM_IN_TIMELOCK)

    # Verify voting has ended.
    poll = sp.local('poll', self.data.poll.open_some())
    sp.verify(sp.level > poll.value.votingEndBlock, Errors.ERROR_VOTING_NOT_FINISHED)

    # Calculate whether voting thresholds were met.
    totalOpinionatedVotes = poll.value.yayVotes + poll.value.nayVotes
    yayVotesNeededForEscrowReturn = (totalOpinionatedVotes * self.data.governanceParameters.minYayVotesPercentForEscrowReturn) // SCALE
    yayVotesNeededForSuperMajority = (totalOpinionatedVotes * self.data.governanceParameters.percentageForSuperMajority) // SCALE

    # Determine where the escrow is released to.
    escrowRecipient = sp.local('escrowRecipient', poll.value.author)
    sp.if poll.value.yayVotes <= yayVotesNeededForEscrowReturn:
      escrowRecipient.value = self.data.communityFundAddress
    
    # Release escrow.
    tokenContractHandle = sp.contract(
      sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
      self.data.tokenContractAddress,
      "transfer"
    ).open_some()
    tokenContractArg = sp.record(
      from_ = sp.self_address, 
      to_ = escrowRecipient.value, 
      value = self.data.governanceParameters.escrowAmount
    )
    sp.transfer(tokenContractArg, sp.mutez(0), tokenContractHandle)

    # Transfer proposal to timelock and update outcome if it passed
    sp.if (poll.value.yayVotes >= yayVotesNeededForSuperMajority) & (poll.value.totalVotes >= self.data.quorum): 
      self.data.timelockItem = sp.some(
        sp.record(
          id = poll.value.id,
          proposal = poll.value.proposal,
          endBlock = sp.level + self.data.governanceParameters.blocksInTimelockForExecution,
          cancelBlock = sp.level + self.data.governanceParameters.blocksInTimelockForCancellation,
          author = poll.value.author
        )
      )

      self.data.outcomes[poll.value.id] = sp.record(
        outcome = PollOutcomes.POLL_OUTCOME_IN_TIMELOCK,
        poll = poll.value
      )
    # Otherwise update the outcomes to show a failure.  
    sp.else:
      self.data.outcomes[poll.value.id] = sp.record(
        outcome = PollOutcomes.POLL_OUTCOME_FAILED,
        poll = poll.value
      )

    # Remove poll.
    self.data.poll = sp.none

    # Calculate a new quorum
    lastWeight = (poll.value.quorum * 80) // SCALE # 80% weight
    newParticipation = (poll.value.totalVotes * 20) // SCALE # 20% weight
    newQuorum = sp.local('newQuorum', newParticipation + lastWeight)

    # Bound upper and lower quorum.
    sp.if newQuorum.value < poll.value.quorumCap.lower:
      newQuorum.value = poll.value.quorumCap.lower

    sp.if newQuorum.value > poll.value.quorumCap.upper:
      newQuorum.value = poll.value.quorumCap.upper

    # Update quorum.
    self.data.quorum = newQuorum.value

  ################################################################
  # Voting
  ################################################################

  @sp.entry_point
  def vote(self, voteValue):
    sp.set_type(voteValue, sp.TNat)

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Verify contract is in the correct state.
    sp.verify(self.data.state == STATE_MACHINE_IDLE, Errors.ERROR_BAD_STATE)

    # Verify a poll is underway.
    sp.verify(self.data.poll.is_some(), Errors.ERROR_NO_POLL)

    # Save state.
    self.data.state = STATE_MACHINE_WAITING_FOR_BALANCE
    self.data.votingState = sp.some(
      sp.record(
        voteValue = voteValue,
        address = sp.sender,
        level = self.data.poll.open_some().votingStartBlock
      )
    )

    # Call token contract.
    tokenContractHandle = sp.contract(
      sp.TPair(
        sp.TRecord(
          address = sp.TAddress,
          level = sp.TNat,
        ),
        sp.TContract(
          sp.TRecord(
            address = sp.TAddress,
            level = sp.TNat,
            result = sp.TNat
          )
        )
      ),
      self.data.tokenContractAddress,
      "getPriorBalance"
    ).open_some()
    tokenContractArg = (
      sp.record(
        address = sp.sender,
        level = self.data.poll.open_some().votingStartBlock,
      ),
      sp.self_entry_point(entry_point = "voteCallback")
    )
    sp.transfer(tokenContractArg, sp.mutez(0), tokenContractHandle)
  
  @sp.entry_point
  def voteCallback(self, returnedData):
    sp.set_type(returnedData, sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat))

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Verify contract is in the correct state.
    sp.verify(self.data.state == STATE_MACHINE_WAITING_FOR_BALANCE, Errors.ERROR_BAD_STATE)

    # Verify sender is the token contract.
    sp.verify(sp.sender == self.data.tokenContractAddress, Errors.ERROR_NOT_TOKEN_CONTRACT)

    # Verify returned data is the requested data.
    savedState = self.data.votingState.open_some()
    sp.verify(savedState.address == returnedData.address, Errors.ERROR_UNKNOWN)
    sp.verify(savedState.level == returnedData.level, Errors.ERROR_UNKNOWN)

    # Verify that the address has not already voted.
    sp.verify(~self.data.poll.open_some().voters.contains(savedState.address), Errors.ERROR_ALREADY_VOTED)
    
    # Verify voting has not ended.
    poll = sp.local('poll', self.data.poll.open_some())
    sp.verify(sp.level <= self.data.poll.open_some().votingEndBlock, Errors.ERROR_VOTING_FINISHED)

    # Retrieve old poll for mutation. 
    newPoll = sp.local('newPoll', self.data.poll.open_some())

    # Add to voters and increment total.
    newPoll.value.voters[savedState.address] = sp.record(
      voteValue = savedState.voteValue,
      level = sp.level,
      votes = returnedData.result
    )
    newPoll.value.totalVotes += returnedData.result

    # Increment the given vote value. Fail if none matched.
    sp.if savedState.voteValue == VoteValue.YAY:
      newPoll.value.yayVotes += returnedData.result
    sp.else:
      sp.if savedState.voteValue == VoteValue.NAY:
        newPoll.value.nayVotes += returnedData.result
      sp.else:
        sp.if savedState.voteValue == VoteValue.ABSTAIN:
          newPoll.value.abstainVotes += returnedData.result
        sp.else:
          sp.failwith(Errors.ERROR_BAD_VOTE_VALUE)

    # Update to new poll
    self.data.poll = sp.some(newPoll.value)

    # Clear state.
    self.data.state = STATE_MACHINE_IDLE
    self.data.votingState = sp.none

  ################################################################
  # Timelock management
  ################################################################

  # Execute a timelock item.
  @sp.entry_point
  def executeTimelock(self, unit):
    sp.set_type(unit, sp.TUnit)

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Verify an item is in the timelock
    sp.verify(self.data.timelockItem.is_some(), Errors.ERROR_NO_ITEM_IN_TIMELOCK)

    # Verify the sender is the author.
    sp.verify(sp.sender == self.data.timelockItem.open_some().author, Errors.ERROR_NOT_AUTHOR)

    # Verify the length of blocks have passed.
    sp.verify(sp.level > self.data.timelockItem.open_some().endBlock, Errors.ERROR_TOO_SOON)

    # Execute the timelock
    operations = self.data.timelockItem.open_some().proposal.proposalLambda(sp.unit)
    sp.set_type(operations, sp.TList(sp.TOperation))
    sp.add_operations(operations)

    # Update the historical outcomes.
    pollId = sp.local('pollId', self.data.timelockItem.open_some().id)
    historicalOutcome = sp.local('historicalOutcome', self.data.outcomes[pollId.value])
    self.data.outcomes[pollId.value] = sp.record(
      poll = historicalOutcome.value.poll, 
      outcome = PollOutcomes.POLL_OUTCOME_EXECUTED
    )

    # Clear the timelock
    self.data.timelockItem = sp.none

  # Cancel a timelock item.
  @sp.entry_point
  def cancelTimelock(self, unit):
    sp.set_type(unit, sp.TUnit)

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Verify an item is in the timelock
    sp.verify(self.data.timelockItem.is_some(), Errors.ERROR_NO_ITEM_IN_TIMELOCK)

    # Verify the length of blocks have passed.
    sp.verify(sp.level >= self.data.timelockItem.open_some().cancelBlock, Errors.ERROR_TOO_SOON)

    # Update the historical outcomes.
    pollId = sp.local('pollId', self.data.timelockItem.open_some().id)
    historicalOutcome = sp.local('historicalOutcome', self.data.outcomes[pollId.value])
    self.data.outcomes[pollId.value] = sp.record(
      poll = historicalOutcome.value.poll, 
      outcome = PollOutcomes.POLL_OUTCOME_CANCELLED
    )
    # Clear the timelock
    self.data.timelockItem = sp.none

  ################################################################
  # Governance
  ################################################################

  # A method to change governance parameters. This method can only be called
  # by this contract.
  @sp.entry_point
  def setParameters(self, newGovernanceParameters):
    sp.set_type(newGovernanceParameters, GOVERNANCE_PARAMETERS_TYPE)

    # Verify that the call did not include XTZ.
    sp.verify(sp.amount == sp.mutez(0), Errors.ERROR_BAD_AMOUNT)

    # Only the DAO can change its own parameters.
    sp.verify(sp.sender == sp.self_address, Errors.ERROR_NOT_DAO)

    # Validate that upper quorum cap is less than 100. Values greater than 100 are unachievable
    # and will result in the DAO being unable to pass proposals.
    # NOTE: Lower quorum cap can't be less than 0, because the Michelson `nat` type ensures numbers are
    # always positive
    sp.verify(newGovernanceParameters.quorumCap.upper <= 100, Errors.ERROR_BAD_DAO_PARAM)

    # Validate that percentages for super majority is less than 100. Values greater than
    # 100 are unachievable and will result in the DAO being unable to pass proposals.
    sp.verify(newGovernanceParameters.percentageForSuperMajority <= 100, Errors.ERROR_BAD_DAO_PARAM)

    # Validate that the percentage of yay votes for escrow return is less than 100. Values greater than
    # 100 are unachievable, and will result in Escrow always being confiscated. 
    sp.verify(newGovernanceParameters.minYayVotesPercentForEscrowReturn <= 100, Errors.ERROR_BAD_DAO_PARAM)

    # Update parameters.
    self.data.governanceParameters = newGovernanceParameters

################################################################
################################################################
# Tests
################################################################
################################################################

# Only run tests if this file is main.
if __name__ == "__main__":

  FakeToken = sp.io.import_script_from_url("file:test-helpers/fake-token.py")
  Store = sp.io.import_script_from_url("file:test-helpers/store.py")
  Token = sp.io.import_script_from_url("file:token.py")

  ################################################################
  # propose
  ################################################################

  @sp.add_test(name="propose - can propose")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a dao contract.
    dao = DaoContract(
      tokenContractAddress = token.address,
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # AND an Alice has tokens
    totalTokens = sp.nat(100)
    scenario += token.mint(
      sp.record(
        address = Addresses.ALICE_ADDRESS,
        value = totalTokens
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # AND Alice has approved the DAO to spend the tokens.
    scenario += token.approve(
      spender = dao.address,
      value = totalTokens
    ).run(
      sender = Addresses.ALICE_ADDRESS
    )

    # AND a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = 0, admin = dao.address)
    scenario += storeContract

    # WHEN Alice makes a proposal. 
    newValue = sp.nat(3)
    def updateLambda(unitParam):
      sp.set_type(unitParam, sp.TUnit)
      storeContractHandle = sp.contract(sp.TNat, storeContract.address, 'replace').open_some()
      sp.result([sp.transfer_operation(newValue, sp.mutez(0), storeContractHandle)])

    title = "Prop 1"
    descriptionLink = "ipfs://xyz"
    descriptionHash = "xyz123"
    proposal = sp.record(
      title = title,
      descriptionLink = descriptionLink,
      descriptionHash = descriptionHash,
      proposalLambda = updateLambda
    )
    
    level = 1

    scenario += dao.propose(proposal).run(
      sender = Addresses.ALICE_ADDRESS,
      level = 1
    )

    # THEN a poll is loaded into the dao.
    scenario.verify(dao.data.poll.is_some())
    poll = dao.data.poll.open_some()

    # AND the proposal matches the input data.
    scenario.verify(poll.proposal.title == title)
    scenario.verify(poll.proposal.descriptionLink == descriptionLink)
    scenario.verify(poll.proposal.descriptionHash == descriptionHash)

    # AND voting totals are zero-ed
    scenario.verify(poll.yayVotes == 0)
    scenario.verify(poll.nayVotes == 0)
    scenario.verify(poll.abstainVotes == 0)
    scenario.verify(poll.totalVotes == 0)

    # AND alice is listed as the author.
    scenario.verify(poll.author == Addresses.ALICE_ADDRESS)

    # AND the poll took the initial identifier
    scenario.verify(poll.id == sp.nat(0))

    # AND the identifier auto-incremented.
    scenario.verify(dao.data.nextProposalId == sp.nat(1))

    # AND the escrow amount is correct.
    scenario.verify(poll.escrowAmount == escrowAmount)

    # AND no voters are listed
    scenario.verify(sp.len(poll.voters) == 0)

    # AND the start and end blocks are set correctly
    expectedStartBlock = level + governanceParameters.voteDelayBlocks
    expectedEndBlock = expectedStartBlock + governanceParameters.voteLengthBlocks
    scenario.verify(poll.votingStartBlock == expectedStartBlock)
    scenario.verify(poll.votingEndBlock == expectedEndBlock)

    # AND the quorum is set correctly. 
    scenario.verify(poll.quorum == dao.data.quorum)

    # AND the quorum caps are set correctly. 
    scenario.verify(poll.quorumCap.lower == governanceParameters.quorumCap.lower)
    scenario.verify(poll.quorumCap.upper == governanceParameters.quorumCap.upper)

    # AND the dao received the tokens in escrow.
    scenario.verify(token.data.balances[dao.address] == escrowAmount)

  @sp.add_test(name="propose - cannot propose if another poll is under vote")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a dao contract.
    dao = DaoContract(
      tokenContractAddress = token.address,
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # AND an Alice and bob have tokens
    numTokens = sp.nat(100)
    scenario += token.mint(
      sp.record(
        address = Addresses.ALICE_ADDRESS,
        value = numTokens
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += token.mint(
      sp.record(
        address = Addresses.BOB_ADDRESS,
        value = numTokens
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # AND Alice and Bob have approved the DAO to spend the tokens.
    scenario += token.approve(
      spender = dao.address,
      value = numTokens
    ).run(
      sender = Addresses.ALICE_ADDRESS
    )
    scenario += token.approve(
      spender = dao.address,
      value = numTokens
    ).run(
      sender = Addresses.BOB_ADDRESS
    )

    # AND a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = sp.nat(0), admin = dao.address)
    scenario += storeContract

    # AND Alice has made a proposal
    newValue = sp.nat(3)
    def updateLambda(unitParam):
      sp.set_type(unitParam, sp.TUnit)
      storeContractHandle = sp.contract(sp.TNat, storeContract.address, 'replace').open_some()
      sp.result([sp.transfer_operation(newValue, sp.mutez(0), storeContractHandle)])

    title = "Prop 1"
    descriptionLink = "ipfs://xyz"
    descriptionHash = "xyz123"
    proposal = sp.record(
      title = title,
      descriptionLink = descriptionLink,
      descriptionHash = descriptionHash,
      proposalLambda = updateLambda
    )
    
    level = 1

    scenario += dao.propose(proposal).run(
      sender = Addresses.ALICE_ADDRESS,
      level = 1
    )

    # WHEN Bob makes a proposal
    newValue = sp.nat(3)
    def updateLambda(unitParam):
      sp.set_type(unitParam, sp.TUnit)
      storeContractHandle = sp.contract(sp.TNat, storeContract.address, 'replace').open_some()
      sp.result([sp.transfer_operation(newValue, sp.mutez(0), storeContractHandle)])

    title = "Prop 2"
    descriptionLink = "ipfs://abc"
    descriptionHash = "abc456"
    proposal = sp.record(
      title = title,
      descriptionLink = descriptionLink,
      descriptionHash = descriptionHash,
      proposalLambda = updateLambda
    )
    
    level = 2

    # THEN the call fails
    scenario += dao.propose(proposal).run(
      sender = Addresses.BOB_ADDRESS,
      level = 1,
      valid = False
    )

  @sp.add_test(name="propose - cannot propose if proposer does not have collateral")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a dao contract.
    dao = DaoContract(
      tokenContractAddress = token.address,
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # AND an Alice has fewer tokens than the escrow amount
    totalTokens = sp.as_nat(escrowAmount - 1)
    scenario += token.mint(
      sp.record(
        address = Addresses.ALICE_ADDRESS,
        value = totalTokens
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # AND Alice has approved the DAO to spend the tokens.
    scenario += token.approve(
      spender = dao.address,
      value = totalTokens
    ).run(
      sender = Addresses.ALICE_ADDRESS
    )

    # AND a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = 0, admin = dao.address)
    scenario += storeContract

    # WHEN Alice makes a proposal. 
    newValue = sp.nat(3)
    def updateLambda(unitParam):
      sp.set_type(unitParam, sp.TUnit)
      storeContractHandle = sp.contract(sp.TNat, storeContract.address, 'replace').open_some()
      sp.result([sp.transfer_operation(newValue, sp.mutez(0), storeContractHandle)])

    title = "Prop 1"
    descriptionLink = "ipfs://xyz"
    descriptionHash = "xyz123"
    proposal = sp.record(
      title = title,
      descriptionLink = descriptionLink,
      descriptionHash = descriptionHash,
      proposalLambda = updateLambda
    )
    
    level = 1

    # THEN the call fails.
    scenario += dao.propose(proposal).run(
      sender = Addresses.ALICE_ADDRESS,
      level = 1,
      valid = False
    )

  ################################################################
  # endVoting
  ################################################################

  @sp.add_test(name="endVoting - fails if no poll underway")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a dao contract.
    dao = DaoContract(
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # WHEN end voting is called before a poll is submitted
    # THEN the call fails.
    scenario += dao.endVoting(sp.unit).run(
      valid = False
    )

  @sp.add_test(name="endVoting - fails if timelock is occupied")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll under is unerway with an item in the timelock
    votingEndBlock = sp.nat(21)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    timelockItem = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      endBlock = sp.nat(10),
      cancelBlock = sp.nat(20),
      author = Addresses.ALICE_ADDRESS
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      timelockItem = sp.some(timelockItem)
    )
    scenario += dao

    # WHEN end voting is called after voting has ended
    # THEN the call fails.
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
      valid = False
    )

  @sp.add_test(name="endVoting - fails if voting is not yet complete")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll is underway
    votingEndBlock = sp.nat(21)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
    )
    scenario += dao

    # WHEN end voting is called before voting has ended
    # THEN the call fails.
    scenario += dao.endVoting(sp.unit).run(
      level = sp.as_nat(votingEndBlock - 1),
      valid = False
    )

  @sp.add_test(name="endVoting - adjusts quorum upwards")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll is underway
    quorum = 45
    votingEndBlock = sp.nat(21)
    totalVotes = 65
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = quorum,
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN quorum is adjusted upwards
    expectedQuorum = 49 # (.8 * lastQuorum) + (.2 * participation) = (.8 * 45) + (.2 * 65) = 36 + 13 = 49
    scenario.verify(dao.data.quorum == expectedQuorum)

  @sp.add_test(name="endVoting - adjusts quorum downwards")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll is underway
    quorum = 65
    votingEndBlock = sp.nat(21)
    totalVotes = 45
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = quorum,
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN quorum is adjusted upwards
    expectedQuorum = 61 # (.8 * lastQuorum) + (.2 * participation) = (.8 * 65) + (.2 * 45) = 52 + 9 = 61
    scenario.verify(dao.data.quorum == expectedQuorum)    

  @sp.add_test(name="endVoting - caps maximum quorum")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters with a conservative upper cap
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumUpperCap = sp.nat(48)
    quorumCap = sp.record(lower = 1, upper = quorumUpperCap)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll is under vote
    quorum = 45
    votingEndBlock = sp.nat(21)
    totalVotes = 65
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = quorum,
      quorumCap = quorumCap,
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN quorum is adjusted upwards and capped at the upper bound
    # Expected = (.8 * lastQuorum) + (.2 * participation) = (.8 * 45) + (.2 * 65) = 36 + 13 = 49
    # Cap = 48
    scenario.verify(dao.data.quorum == quorumUpperCap)

  @sp.add_test(name="endVoting - caps minimum quorum")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters with a conservative lower cap
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll is underway
    quorum = 65
    votingEndBlock = sp.nat(21)
    totalVotes = 45
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = quorum,
      quorumCap = quorumCap
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN quorum is adjusted downwards and capped at the lower bound
    # Expected = (.8 * lastQuorum) + (.2 * participation) = (.8 * 65) + (.2 * 45) = 52 + 9 = 61
    # Cap = 62
    scenario.verify(dao.data.quorum == quorumLowerCap)

  @sp.add_test(name="endVoting - returns escrow to author")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters 
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll by Alice which achieves the minimum for escrow return
    votingEndBlock = sp.nat(21)
    totalVotes = 100
    yayVotes = 40
    nayVotes = 60
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = yayVotes,
      nayVotes = nayVotes,
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = quorumCap
    )

    # AND a token contract.
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token

    # AND a dao contract with the parameters above.
    quorum = 65
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum,
      tokenContractAddress = token.address,
    )
    scenario += dao

    # AND the dao has tokens escrowed
    scenario += token.mint(
      sp.record(
        address = dao.address,
        value = escrowAmount
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN alice receives the escrow.
    scenario.verify(token.data.balances[Addresses.ALICE_ADDRESS] == escrowAmount)
    scenario.verify(token.data.balances[dao.address] == 0)
    
  @sp.add_test(name="endVoting - gives escrow to community fund on failure")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters 
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll by Alice which fails to achieve the minimum for escrow return
    votingEndBlock = sp.nat(21)
    totalVotes = 100
    yayVotes = 19
    nayVotes = 81
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = yayVotes,
      nayVotes = nayVotes,
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = quorumCap
    )

    # AND a token contract.
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token

    # AND a dao contract with the parameters above.
    quorum = 65
    dao = DaoContract(
      communityFundAddress = Addresses.COMMUNITY_FUND_ADDRESS,
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum,
      tokenContractAddress = token.address,
    )
    scenario += dao

    # AND the dao has tokens escrowed
    scenario += token.mint(
      sp.record(
        address = dao.address,
        value = escrowAmount
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN the community fund receives the escrow.
    scenario.verify(token.data.balances[Addresses.COMMUNITY_FUND_ADDRESS] == escrowAmount)
    scenario.verify(token.data.balances[dao.address] == 0)

  @sp.add_test(name="endVoting - removes poll if quorum and super majority not met")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters 
    quorum = 100
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll by Alice which fails to achieve quorum and fails to achieve a super majority
    votingEndBlock = sp.nat(21)
    totalVotes = quorum // 2
    yayVotes = totalVotes // 2
    nayVotes = totalVotes // 2
    pollId = sp.nat(0)
    poll = sp.record(
      id = pollId,
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = yayVotes,
      nayVotes = nayVotes,
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = quorumCap
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum,
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN the poll is removed 
    scenario.verify(~dao.data.poll.is_some())

    # AND the outcome for the poll is FAILED
    scenario.verify(dao.data.outcomes[pollId].outcome == PollOutcomes.POLL_OUTCOME_FAILED)

    # AND it was not moved to the timelock
    scenario.verify(~dao.data.timelockItem.is_some())

  @sp.add_test(name="endVoting - removes poll if super majority achieved but quorum not met")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters 
    quorum = 100
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll by Alice which fails to achieve quorum and but achieved a super majority
    votingEndBlock = sp.nat(21)
    totalVotes = quorum // 2
    yayVotes = totalVotes
    nayVotes = 0
    pollId = sp.nat(0)
    poll = sp.record(
      id = pollId,
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = yayVotes,
      nayVotes = nayVotes,
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = quorumCap
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum,
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN the poll under vote is removed 
    scenario.verify(~dao.data.poll.is_some())

    # AND the outcome for the poll is FAILED
    scenario.verify(dao.data.outcomes[pollId].outcome == PollOutcomes.POLL_OUTCOME_FAILED)

    # AND it was not moved to the timelock
    scenario.verify(~dao.data.timelockItem.is_some())    

  @sp.add_test(name="endVoting - removes poll if quorum met and super majority not achieved")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters 
    quorum = 100
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll by Alice which achieves quorum and but failed to achieved a super majority
    votingEndBlock = sp.nat(21)
    totalVotes = quorum * 2
    yayVotes = sp.nat(10)
    nayVotes = sp.as_nat(totalVotes - yayVotes)
    pollId = sp.nat(0)
    poll = sp.record(
      id = pollId,
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = yayVotes,
      nayVotes = nayVotes,
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = quorumCap
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum,
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN the poll under vote is removed 
    scenario.verify(~dao.data.poll.is_some())

    # AND the outcome for the poll is FAILED
    scenario.verify(dao.data.outcomes[pollId].outcome == PollOutcomes.POLL_OUTCOME_FAILED)

    # AND it was not moved to the timelock
    scenario.verify(~dao.data.timelockItem.is_some())    

  @sp.add_test(name="endVoting - moves proposal to timelock if super majority and quorum are achieved")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters 
    quorum = 200
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumLowerCap = 62
    quorumCap = sp.record(lower = quorumLowerCap, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a poll by Alice which achieves quorum and but failed to achieved a super majority
    votingEndBlock = sp.nat(21)
    totalVotes = quorum # 200
    yayVotes = 160 # 80% of 200
    nayVotes = 40
    proposalTitle = "proposal which will succeed"
    pollId = sp.nat(0)
    poll = sp.record(
      id = pollId,
      proposal = sp.record(
        title = proposalTitle,
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = yayVotes,
      nayVotes = nayVotes,
      abstainVotes = sp.nat(0),
      totalVotes = totalVotes,
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = escrowAmount,
      quorum = sp.nat(100),
      quorumCap = quorumCap
    )

    # AND a dao contract with the parameters above.
    dao = DaoContract(
      governanceParameters = governanceParameters,
      poll = sp.some(poll),
      quorum = quorum,
    )
    scenario += dao

    # WHEN end voting is called
    scenario += dao.endVoting(sp.unit).run(
      level = votingEndBlock + 1,
    )    

    # THEN the poll is removed 
    scenario.verify(~dao.data.poll.is_some())

    # AND the outcome for the poll is IN_TIMELOCK
    scenario.verify(dao.data.outcomes[pollId].outcome == PollOutcomes.POLL_OUTCOME_IN_TIMELOCK)

    # AND the proposal was moved to the timelock
    scenario.verify(dao.data.timelockItem.is_some())    
    scenario.verify(dao.data.timelockItem.open_some().proposal.title == proposalTitle)

  ################################################################
  # vote
  ################################################################

  @sp.add_test(name="vote - fails if in bad state")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll.
    votingStartBlock = sp.nat(11)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = votingStartBlock,
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract in the STATE_MACHINE_WAITING_FOR_BALANCE state
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = votingStartBlock,
      voteValue = VoteValue.YAY
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN vote is called
    # THEN the call fails.
    scenario += dao.vote(VoteValue.YAY).run(
      sender = Addresses.VOTER_ADDRESS,
      valid = False
    )

  @sp.add_test(name="vote - fails if no poll under vote")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN a dao contract with no poll.
    dao = DaoContract(
      poll = sp.none,
      state = STATE_MACHINE_IDLE,
      votingState = sp.none
    )
    scenario += dao

    # WHEN vote is called
    # THEN the call fails.
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = sp.nat(1),
      result = sp.nat(50)
    )
    scenario += dao.vote(VoteValue.YAY).run(
      sender = Addresses.VOTER_ADDRESS,
      valid = False
    )

  @sp.add_test(name="vote - succeeds at casting a vote")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN a poll.
    votingStartBlock = sp.nat(11)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = votingStartBlock,
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    # AND a fake token contract
    votingPower = sp.nat(50)
    token = FakeToken.FakeTokenContract(result = votingPower)
    scenario += token

    # AND and a dao contract holding the poll.
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_IDLE,
      tokenContractAddress = token.address,
      votingState = sp.none
    )
    scenario += dao

    # WHEN vote is called
    scenario += dao.vote(VoteValue.YAY).run(
      sender = Addresses.VOTER_ADDRESS,
      level = votingStartBlock + 1,
    )

    # THEN the vote tallies are incremented.
    scenario.verify(dao.data.poll.open_some().yayVotes == votingPower)
    scenario.verify(dao.data.poll.open_some().nayVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().abstainVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().totalVotes == votingPower)

    # AND the VOTER_ADDRESS was recorded
    scenario.verify(dao.data.poll.open_some().voters.contains(Addresses.VOTER_ADDRESS))

    # AND the state machine is reset
    scenario.verify(dao.data.state == STATE_MACHINE_IDLE)
    scenario.verify(~dao.data.votingState.is_some())

  ################################################################
  # voteCallback
  ################################################################

  @sp.add_test(name="voteCallback - fails if in bad state")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract in the STATE_MACHINE_IDLE state
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_IDLE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.none
    )
    scenario += dao

    # WHEN voteCallback is called
    # THEN the call fails.
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = sp.nat(1),
      result = sp.nat(50)
    )
    scenario += dao.voteCallback(result).run(
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
      valid = False
    )

  @sp.add_test(name="voteCallback - fails if not called by token contract")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = sp.nat(1),
      voteValue = VoteValue.YAY
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called by someone other than the token contract
    # THEN the call fails.
    notTokenContract = Addresses.NULL_ADDRESS
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = sp.nat(1),
      result = sp.nat(50)
    )
    scenario += dao.voteCallback(result).run(
      sender = notTokenContract,
      valid = False
    )  

  @sp.add_test(name="voteCallback - fails if callback contains bad address")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract
    voteRequestLevel = sp.nat(1)
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = VoteValue.YAY
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called by with an address other than the address requested
    # THEN the call fails.
    result = sp.record(
      address = Addresses.NULL_ADDRESS,
      level = voteRequestLevel,
      result = sp.nat(50)
    )
    scenario += dao.voteCallback(result).run(
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
      valid = False
    )    

  @sp.add_test(name="voteCallback - fails if callback contains bad level")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract
    voteRequestLevel = sp.nat(1)
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = VoteValue.YAY
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called by with a level other than the level requested
    # THEN the call fails.
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel + 1,
      result = sp.nat(50)
    )
    scenario += dao.voteCallback(result).run(
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
      valid = False
    )

  @sp.add_test(name="voteCallback - fails if already voted")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll where the VOTER_ADDRESS has voted
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = sp.map(
        l = {
          Addresses.VOTER_ADDRESS: sp.record(
            voteValue = VoteValue.YAY,
            level = sp.nat(12),
            votes = sp.nat(200),
          )
        }
      ),
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract
    voteRequestLevel = sp.nat(1)
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = VoteValue.YAY
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called by the VOTER_ADDRESS
    # THEN the call fails.
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      result = sp.nat(50)
    )
    scenario += dao.voteCallback(result).run(
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
      valid = False
    )

  @sp.add_test(name="voteCallback - fails if voting finished")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll
    votingEndBlock = sp.nat(30)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = votingEndBlock,
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract
    voteRequestLevel = sp.nat(1)
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = VoteValue.YAY
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called after the voting has ended
    # THEN the call fails.
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      result = sp.nat(50)
    )
    scenario += dao.voteCallback(result).run(
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
      level = votingEndBlock + 1,
      valid = False
    )    

  @sp.add_test(name="voteCallback - correctly tabulates yay votes")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll where the VOTER_ADDRESS has voted
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract with a yay vote
    voteRequestLevel = sp.nat(1)
    voteValue = VoteValue.YAY
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = voteValue
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called
    votingPower = sp.nat(50)
    voteLevel = sp.nat(20)
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      result = votingPower
    )
    scenario += dao.voteCallback(result).run(
      level = voteLevel,
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
    )

    # THEN the vote tallies are incremented.
    scenario.verify(dao.data.poll.open_some().yayVotes == votingPower)
    scenario.verify(dao.data.poll.open_some().nayVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().abstainVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().totalVotes == votingPower)

    # AND the VOTER_ADDRESS was recorded with the correct metadata.
    scenario.verify(dao.data.poll.open_some().voters.contains(Addresses.VOTER_ADDRESS))
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].voteValue == voteValue)
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].level == voteLevel)
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].votes == votingPower)

    # AND the state machine is reset
    scenario.verify(dao.data.state == STATE_MACHINE_IDLE)
    scenario.verify(~dao.data.votingState.is_some())

  @sp.add_test(name="voteCallback - correctly tabulates nay votes")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll where the VOTER_ADDRESS has voted
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract with a nay vote
    voteRequestLevel = sp.nat(1)
    voteValue = VoteValue.NAY
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = voteValue
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called
    votingPower = sp.nat(50)
    voteLevel = sp.nat(20)
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      result = votingPower
    )
    scenario += dao.voteCallback(result).run(
      level = voteLevel,
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
    )

    # THEN the vote tallies are incremented.
    scenario.verify(dao.data.poll.open_some().yayVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().nayVotes == votingPower)
    scenario.verify(dao.data.poll.open_some().abstainVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().totalVotes == votingPower)

    # AND the VOTER_ADDRESS was recorded with the correct metadata.
    scenario.verify(dao.data.poll.open_some().voters.contains(Addresses.VOTER_ADDRESS))
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].voteValue == voteValue)
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].level == voteLevel)
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].votes == votingPower)

    # AND the state machine is reset
    scenario.verify(dao.data.state == STATE_MACHINE_IDLE)
    scenario.verify(~dao.data.votingState.is_some())

  @sp.add_test(name="voteCallback - correctly tabulates abstain votes")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a poll where the VOTER_ADDRESS has voted
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'title',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(11),
      votingEndBlock = sp.nat(20),
      yayVotes = sp.nat(0),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(0),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(50),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )    

    # AND a dao contract with an abstain vote
    voteRequestLevel = sp.nat(1)
    voteValue = VoteValue.ABSTAIN
    votingState = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      voteValue = voteValue
    )
    dao = DaoContract(
      poll = sp.some(poll),
      state = STATE_MACHINE_WAITING_FOR_BALANCE,
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      votingState = sp.some(votingState)
    )
    scenario += dao

    # WHEN voteCallback is called
    votingPower = sp.nat(50)
    voteLevel = sp.nat(20)
    result = sp.record(
      address = Addresses.VOTER_ADDRESS,
      level = voteRequestLevel,
      result = votingPower
    )
    scenario += dao.voteCallback(result).run(
      level = voteLevel,
      sender = Addresses.TOKEN_CONTRACT_ADDRESS,
    )

    # THEN the vote tallies are incremented.
    scenario.verify(dao.data.poll.open_some().yayVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().nayVotes == sp.nat(0))
    scenario.verify(dao.data.poll.open_some().abstainVotes == votingPower)
    scenario.verify(dao.data.poll.open_some().totalVotes == votingPower)

    # AND the VOTER_ADDRESS was recorded with the correct metadata.
    scenario.verify(dao.data.poll.open_some().voters.contains(Addresses.VOTER_ADDRESS))
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].voteValue == voteValue)
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].level == voteLevel)
    scenario.verify(dao.data.poll.open_some().voters[Addresses.VOTER_ADDRESS].votes == votingPower)

    # AND the state machine is reset
    scenario.verify(dao.data.state == STATE_MACHINE_IDLE)
    scenario.verify(~dao.data.votingState.is_some())

  ###############################################################
  # executeTimelock
  ###############################################################

  @sp.add_test(name="executeTimelock - fails if no item in timelock")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a dao contract without an item in the timelock
    dao = DaoContract(
      timelockItem = sp.none
    )
    scenario += dao

    # WHEN executeTimelock is called
    # THEN the call fails.
    scenario += dao.executeTimelock(sp.unit).run(
      valid = False
    )
  
  @sp.add_test(name="executeTimelock - fails if before endBlock")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN an item in the timelock
    endBlock = sp.nat(10)
    cancelBlock = sp.nat(20)
    timelockItem = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      endBlock = endBlock,
      cancelBlock = cancelBlock,
      author = Addresses.ALICE_ADDRESS
    )

    # AND a dao contract with the item.
    dao = DaoContract(
      timelockItem = sp.some(timelockItem)
    )
    scenario += dao

    # WHEN executeTimelock is called before the endblock
    # THEN the call fails.
    scenario += dao.executeTimelock(sp.unit).run(
      level = sp.as_nat(endBlock - 1),
      sender = Addresses.ALICE_ADDRESS,
      valid = False
    )

  @sp.add_test(name="executeTimelock - fails if not called by author")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN an item in the timelock
    endBlock = sp.nat(10)
    cancelBlock = sp.nat(20)
    timelockItem = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      endBlock = endBlock,
      cancelBlock = cancelBlock,
      author = Addresses.ALICE_ADDRESS
    )

    # AND a dao contract with the item.
    dao = DaoContract(
      timelockItem = sp.some(timelockItem)
    )
    scenario += dao

    # WHEN executeTimelock is called by someone other than the author
    # THEN the call fails.
    notAuthor = Addresses.NULL_ADDRESS
    scenario += dao.executeTimelock(sp.unit).run(
      level = endBlock + 1,
      sender = notAuthor,
      valid = False
    )

  @sp.add_test(name="executeTimelock - can execute proposal")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = 0, admin = Addresses.TOKEN_ADMIN_ADDRESS)
    scenario += storeContract

    # AND an item in the timelock
    newValue = sp.nat(3)
    def updateLambda(unitParam):
      sp.set_type(unitParam, sp.TUnit)
      storeContractHandle = sp.contract(sp.TNat, storeContract.address, 'replace').open_some()
      sp.result([sp.transfer_operation(newValue, sp.mutez(0), storeContractHandle)])    

    pollId = sp.nat(0)
    endBlock = sp.nat(10)
    cancelBlock = sp.nat(20)
    timelockItem = sp.record(
      id = pollId,
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = updateLambda
      ),
      endBlock = endBlock,
      cancelBlock = cancelBlock,
      author = Addresses.ALICE_ADDRESS
    )

    poll = sp.record(
      id = pollId,
      proposal = sp.record(
        title = "timelocked prop",
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(1),
      votingEndBlock = sp.nat(5),
      yayVotes = sp.nat(100),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(100),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(2),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(0), upper = sp.nat(1000))
    )

    # AND a dao contract with the item.
    dao = DaoContract(
      timelockItem = sp.some(timelockItem),
      outcomes = sp.big_map(
        l = {
            pollId: sp.record(
              outcome = PollOutcomes.POLL_OUTCOME_IN_TIMELOCK,
              poll = poll
            )
        },
        tkey = sp.TNat,
        tvalue = HistoricalOutcomes.HISTORICAL_OUTCOME_TYPE,
      )
    )
    scenario += dao

    # AND the store contract has the dao as the admin.
    scenario += storeContract.setAdmin(dao.address)

    # WHEN executeTimelock is called by the author after the endBlock
    notAuthor = Addresses.NULL_ADDRESS
    scenario += dao.executeTimelock(sp.unit).run(
      level = endBlock + 1,
      sender = Addresses.ALICE_ADDRESS,
    )

    # THEN the proposal executed
    scenario.verify(storeContract.data.storedValue == newValue)

    # AND the historical outcome is updated.
    scenario.verify(dao.data.outcomes[pollId].outcome == PollOutcomes.POLL_OUTCOME_EXECUTED)

    # AND the timelock is empty.
    scenario.verify(~dao.data.timelockItem.is_some())

  ################################################################
  # cancelTimelock
  ################################################################

  @sp.add_test(name="cancelTimelock - fails if no item in timelock")
  def test():
    scenario = sp.test_scenario()
    
    # GIVEN a dao contract without an item in the timelock
    dao = DaoContract(
      timelockItem = sp.none
    )
    scenario += dao

    # WHEN cancelTimelock is called
    # THEN the call fails.
    scenario += dao.cancelTimelock(sp.unit).run(
      valid = False
    )
  
  @sp.add_test(name="cancelTimelock - fails if before cancelBlock")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN an item in the timelock
    endBlock = sp.nat(10)
    cancelBlock = sp.nat(20)
    timelockItem = sp.record(
      id = sp.nat(0), 
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      endBlock = endBlock,
      cancelBlock = cancelBlock,
      author = Addresses.ALICE_ADDRESS
    )

    # AND a dao contract with the item.
    dao = DaoContract(
      timelockItem = sp.some(timelockItem)
    )
    scenario += dao

    # WHEN cancelTimelock is called before the cancelBlock
    # THEN the call fails.
    scenario += dao.cancelTimelock(sp.unit).run(
      level = sp.as_nat(cancelBlock - 1),
      valid = False
    )

  @sp.add_test(name="cancelTimelock - can cancel timelock")
  def test():
    scenario = sp.test_scenario()
  
    # GIVEN an item in the timelock
    endBlock = sp.nat(10)
    cancelBlock = sp.nat(20)
    pollId = sp.nat(0)
    timelockItem = sp.record(
      id = pollId,
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      endBlock = endBlock,
      cancelBlock = cancelBlock,
      author = Addresses.ALICE_ADDRESS
    )

    poll = sp.record(
      id = pollId,
      proposal = sp.record(
        title = "timelocked prop",
        descriptionLink = 'ipfs://xyz',
        descriptionHash = "xyz123",
        proposalLambda = sp.build_lambda(lambda x: sp.list(l = [], t = sp.TOperation))
      ),
      votingStartBlock = sp.nat(1),
      votingEndBlock = sp.nat(5),
      yayVotes = sp.nat(100),
      nayVotes = sp.nat(0),
      abstainVotes = sp.nat(0),
      totalVotes = sp.nat(100),
      voters = {},
      author = Addresses.ALICE_ADDRESS,
      escrowAmount = sp.nat(2),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(0), upper = sp.nat(1000))
    )

    # AND a dao contract with the item.
    dao = DaoContract(
      timelockItem = sp.some(timelockItem),
      outcomes = sp.big_map(
        l = {
            pollId: sp.record(
              outcome = PollOutcomes.POLL_OUTCOME_IN_TIMELOCK,
              poll = poll
            )
        },
        tkey = sp.TNat,
        tvalue = HistoricalOutcomes.HISTORICAL_OUTCOME_TYPE,
      )
    )
    scenario += dao

    # WHEN cancelTimelock is called at the cancelBlock
    scenario += dao.cancelTimelock(sp.unit).run(
      level = cancelBlock
    )    

    # AND the historical outcome is updated.
    scenario.verify(dao.data.outcomes[pollId].outcome == PollOutcomes.POLL_OUTCOME_CANCELLED)

    # THEN the item is removed.
    scenario.verify(~dao.data.timelockItem.is_some())

  ################################################################
  # setParameters
  ################################################################

  @sp.add_test(name="setParameters - can set new parameters")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a dao contract.
    dao = DaoContract(
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # WHEN the DAO contract rotates the governance parameters
    newEscrowAmount = sp.nat(12)
    newVoteDelayBlocks = sp.nat(2)
    newVoteLengthBlocks = sp.nat(11)
    newminYayVotesPercentForEscrowReturn = sp.nat(21)
    newblocksInTimelockForExecution = sp.nat(31)
    newblocksInTimelockForCancellation = sp.nat(41)
    newPercentageForSuperMajority = sp.nat(81)
    newQuorumCap = sp.record(lower = 2, upper = 98)
    newGovernanceParameters = sp.record(
      escrowAmount = newEscrowAmount,
      voteDelayBlocks = newVoteDelayBlocks,
      voteLengthBlocks = newVoteLengthBlocks,
      minYayVotesPercentForEscrowReturn = newminYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = newblocksInTimelockForExecution,
      blocksInTimelockForCancellation = newblocksInTimelockForCancellation,
      percentageForSuperMajority = newPercentageForSuperMajority,
      quorumCap = newQuorumCap
    )

    scenario += dao.setParameters(newGovernanceParameters).run(
      sender = dao.address
    )

    # THEN the parameters are rotated.
    scenario.verify(dao.data.governanceParameters.escrowAmount == newEscrowAmount)
    scenario.verify(dao.data.governanceParameters.voteDelayBlocks == newVoteDelayBlocks)
    scenario.verify(dao.data.governanceParameters.voteLengthBlocks == newVoteLengthBlocks)
    scenario.verify(dao.data.governanceParameters.minYayVotesPercentForEscrowReturn == newminYayVotesPercentForEscrowReturn)
    scenario.verify(dao.data.governanceParameters.blocksInTimelockForExecution == newblocksInTimelockForExecution)
    scenario.verify(dao.data.governanceParameters.blocksInTimelockForCancellation == newblocksInTimelockForCancellation)
    scenario.verify(dao.data.governanceParameters.percentageForSuperMajority == newPercentageForSuperMajority)
    scenario.verify(dao.data.governanceParameters.quorumCap.lower == newQuorumCap.lower)
    scenario.verify(dao.data.governanceParameters.quorumCap.upper == newQuorumCap.upper)

  @sp.add_test(name="setParameters - fails if not called by dao")
  def test():
    scenario = sp.test_scenario()
    
    # Given some governance parameters
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

    # AND a dao contract.
    dao = DaoContract(
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # WHEN new governance parameters are set by someone other than the dao
    # THEN the call fails.
    newEscrowAmount = sp.nat(12)
    newVoteDelayBlocks = sp.nat(2)
    newVoteLengthBlocks = sp.nat(11)
    newminYayVotesPercentForEscrowReturn = sp.nat(21)
    newblocksInTimelockForExecution = sp.nat(31)
    newblocksInTimelockForCancellation = sp.nat(41)
    newPercentageForSuperMajority = sp.nat(81)
    newQuorumCap = sp.record(lower = 2, upper = 98)
    newGovernanceParameters = sp.record(
      escrowAmount = newEscrowAmount,
      voteDelayBlocks = newVoteDelayBlocks,
      voteLengthBlocks = newVoteLengthBlocks,
      minYayVotesPercentForEscrowReturn = newminYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = newblocksInTimelockForExecution,
      blocksInTimelockForCancellation = newblocksInTimelockForCancellation,
      percentageForSuperMajority = newPercentageForSuperMajority,
      quorumCap = newQuorumCap
    )

    notDao = Addresses.NULL_ADDRESS
    scenario += dao.setParameters(newGovernanceParameters).run(
      sender = notDao,
      valid = False
    )

  @sp.add_test(name="setParameters - fails if upper quorum cap is above 100")
  def test():
    scenario = sp.test_scenario()
    
    # Given governance parameters with a quorum cap greater than 100
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

        # AND a dao contract.
    dao = DaoContract(
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # WHEN the DAO contract tries to rotate the parameters to have a quorum cap 
    # that is above 100.
    newQuorumCap = sp.record(lower = 2, upper = 105)

    newEscrowAmount = sp.nat(12)
    newVoteDelayBlocks = sp.nat(2)
    newVoteLengthBlocks = sp.nat(11)
    newminYayVotesPercentForEscrowReturn = sp.nat(21)
    newblocksInTimelockForExecution = sp.nat(31)
    newblocksInTimelockForCancellation = sp.nat(41)
    newPercentageForSuperMajority = sp.nat(81)
    newGovernanceParameters = sp.record(
      escrowAmount = newEscrowAmount,
      voteDelayBlocks = newVoteDelayBlocks,
      voteLengthBlocks = newVoteLengthBlocks,
      minYayVotesPercentForEscrowReturn = newminYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = newblocksInTimelockForExecution,
      blocksInTimelockForCancellation = newblocksInTimelockForCancellation,
      percentageForSuperMajority = newPercentageForSuperMajority,
      quorumCap = newQuorumCap
    )

    # THEN the call fails
    scenario += dao.setParameters(newGovernanceParameters).run(
      sender = dao.address,
      valid = False
    )

  @sp.add_test(name="setParameters - fails if super majority is above 100")
  def test():
    scenario = sp.test_scenario()
    
    # Given governance parameters with a quorum cap greater than 100
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

        # AND a dao contract.
    dao = DaoContract(
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # WHEN the DAO contract tries to rotate the parameters to have a super majority 
    # that is above 100.
    newPercentageForSuperMajority = sp.nat(105)

    newEscrowAmount = sp.nat(12)
    newVoteDelayBlocks = sp.nat(2)
    newVoteLengthBlocks = sp.nat(11)
    newminYayVotesPercentForEscrowReturn = sp.nat(21)
    newblocksInTimelockForExecution = sp.nat(31)
    newblocksInTimelockForCancellation = sp.nat(41)
    newQuorumCap = sp.record(lower = 2, upper = 105)
    newGovernanceParameters = sp.record(
      escrowAmount = newEscrowAmount,
      voteDelayBlocks = newVoteDelayBlocks,
      voteLengthBlocks = newVoteLengthBlocks,
      minYayVotesPercentForEscrowReturn = newminYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = newblocksInTimelockForExecution,
      blocksInTimelockForCancellation = newblocksInTimelockForCancellation,
      percentageForSuperMajority = newPercentageForSuperMajority,
      quorumCap = newQuorumCap
    )

    # THEN the call fails
    scenario += dao.setParameters(newGovernanceParameters).run(
      sender = dao.address,
      valid = False
    )

  @sp.add_test(name="setParameters - fails if min yay votes for escrow return is above 100")
  def test():
    scenario = sp.test_scenario()
    
    # Given governance parameters with a quorum cap greater than 100
    escrowAmount = sp.nat(10)
    voteDelayBlocks = sp.nat(1)
    voteLengthBlocks = sp.nat(10)
    minYayVotesPercentForEscrowReturn = sp.nat(20)
    blocksInTimelockForExecution = sp.nat(30)
    blocksInTimelockForCancellation = sp.nat(40)
    percentageForSuperMajority = sp.nat(80)
    quorumCap = sp.record(lower = 1, upper = 99)
    governanceParameters = sp.record(
      escrowAmount = escrowAmount,
      voteDelayBlocks = voteDelayBlocks,
      voteLengthBlocks = voteLengthBlocks,
      minYayVotesPercentForEscrowReturn = minYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = blocksInTimelockForExecution,
      blocksInTimelockForCancellation = blocksInTimelockForCancellation,
      percentageForSuperMajority = percentageForSuperMajority,
      quorumCap = quorumCap
    )

        # AND a dao contract.
    dao = DaoContract(
      governanceParameters = governanceParameters,
    )
    scenario += dao

    # WHEN the DAO contract tries to rotate the parameters to have a min yay votes
    # for escrow return that is above 100.
    newminYayVotesPercentForEscrowReturn = sp.nat(105)

    newEscrowAmount = sp.nat(12)
    newVoteDelayBlocks = sp.nat(2)
    newVoteLengthBlocks = sp.nat(11)
    newblocksInTimelockForExecution = sp.nat(31)
    newblocksInTimelockForCancellation = sp.nat(41)
    newPercentageForSuperMajority = sp.nat(105)
    newQuorumCap = sp.record(lower = 2, upper = 105)
    newGovernanceParameters = sp.record(
      escrowAmount = newEscrowAmount,
      voteDelayBlocks = newVoteDelayBlocks,
      voteLengthBlocks = newVoteLengthBlocks,
      minYayVotesPercentForEscrowReturn = newminYayVotesPercentForEscrowReturn,
      blocksInTimelockForExecution = newblocksInTimelockForExecution,
      blocksInTimelockForCancellation = newblocksInTimelockForCancellation,
      percentageForSuperMajority = newPercentageForSuperMajority,
      quorumCap = newQuorumCap
    )

    # THEN the call fails
    scenario += dao.setParameters(newGovernanceParameters).run(
      sender = dao.address,
      valid = False
    )


  sp.add_compilation_target("dao", DaoContract())
