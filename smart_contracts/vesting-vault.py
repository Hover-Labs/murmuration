import smartpy as sp

# TODO(keefertaylor): Dedupe me.

Proposal = sp.import_script_from_url("file:common/proposal.py")
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


# A type representing a quorum cap. 
# Params:
# - lower (nat): The lower bound
# - upper (nat): The upper bound
QUORUM_CAP_TYPE = sp.TRecord(
  lower = sp.TNat, 
  upper = sp.TNat
).layout(("lower", "upper")) 


################################################################
################################################################
# Poll Outcomes
################################################################
################################################################

POLL_OUTCOME_FAILED = 0       # Did not pass voting
POLL_OUTCOME_IN_TIMELOCK = 1  # Passed voting, is in timelock
POLL_OUTCOME_EXECUTED = 2     # Passed voting, executed in timelock
POLL_OUTCOME_CANCELLED = 3    # Passed voting, but cancelled from timelock

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
  voters = sp.TMap(sp.TAddress, VOTE_RECORD_TYPE),
  author = sp.TAddress,
  escrowAmount = sp.TNat,
  quorum = sp.TNat,
  quorumCap = QUORUM_CAP_TYPE
).layout(("id", ("proposal", ("votingStartBlock", ("votingEndBlock", ("yayVotes", ("nayVotes", ("abstainVotes", ("totalVotes", ("voters", ("author", ("escrowAmount", ("quorum", "quorumCap")))))))))))))


# A historical result of a vote.
# Params:
# - outcome (nat): The outcome of the poll
# - poll (POLL_TYPE): The poll and the results.
HISTORICAL_OUTCOME_TYPE = sp.TRecord(
  outcome = sp.TNat,
  poll = POLL_TYPE
).layout(("outcome", "poll"))

################################################################
################################################################
# Contract
################################################################
################################################################

Addresses = sp.import_script_from_url("file:./test-helpers/addresses.py")
Proposal = sp.import_script_from_url("file:./common/proposal.py")

# A simple vesting contract.
class VestingVault(sp.Contract):
    def __init__(
      self,
      # The amount which becomes available per block.
      amountPerBlock = sp.nat(1),
      # The block which vesting start on.
      startBlock = sp.nat(12),
      # The owner.
      owner = Addresses.OWNER_ADDRESS,
      # The governor.
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      # The token contract.
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      # The dao address.
      daoContractAddress = Addresses.DAO_ADDRESS
    ):
        metadata_data = sp.bytes_of_string('{"name": "kDAO Vesting Contract", "description": "kDAO Vesting Contract", "authors": ["Hover Labs <hello@hover.engineering>"], "homepage":  "https://kolibri.finance" }')

        metadata = sp.big_map(
            l = {
                "": sp.bytes('0x74657a6f732d73746f726167653a64617461'), # "tezos-storage:data"
                "data": metadata_data
            },
            tkey = sp.TString,
            tvalue = sp.TBytes            
        )

        self.init(
          # The amount redeemable per block.
          amountPerBlock = amountPerBlock,
          # The last block a withdrawal was processed.
          startBlock = startBlock,
          # The culmulative amount withdrawn
          amountWithdrawn = sp.nat(0),
          # The governor.
          governorAddress = governorAddress,
          # The user who can redeem funds.
          owner = owner,
          # The token contract to redeem from. 
          tokenContractAddress = tokenContractAddress,
          # The dao contract for proposing and voting.
          daoContractAddress = daoContractAddress,
          # Metadata
          metadata = metadata,
        )

    ################################################################
    # Vesting
    ################################################################

    # Withdraw a number of vested tokens.
    @sp.entry_point	
    def withdraw(self, params):
      sp.set_type(params, sp.TRecord(numberOfTokens = sp.TNat).layout("numberOfTokens"))

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "NOT_OWNER")

      # Verify the requester can withdraw the amount of tokens.
      numberOfBlocksElapsed = sp.as_nat(sp.level - self.data.startBlock)
      maximumAmountAllowed = numberOfBlocksElapsed * self.data.amountPerBlock
      totalWithdrawn = self.data.amountWithdrawn + params.numberOfTokens
      sp.verify(totalWithdrawn <= maximumAmountAllowed, "NOT_VESTED")

      # Update amount withdrawn
      self.data.amountWithdrawn = totalWithdrawn

      # Request tokens transferred to recipient.
      handle = sp.contract(
        sp.TRecord(
          from_ = sp.TAddress,
          to_ = sp.TAddress, 
          value = sp.TNat
        ).layout(("from_ as from", ("to_ as to", "value"))),
        self.data.tokenContractAddress,
        "transfer"
      ).open_some()
      arg = sp.record(from_ = sp.self_address, to_ = sp.sender, value = params.numberOfTokens)
      sp.transfer(arg, sp.mutez(0), handle)

    ################################################################
    # Recovery Functions
    # Useful in case XTZ is sent or tokens are airdropped 
    ################################################################

    # Rescue XTZ
    @sp.entry_point	
    def rescueXTZ(self, params):
      sp.set_type(params, sp.TRecord(destinationAddress = sp.TAddress).layout("destinationAddress"))

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "NOT_OWNER")

      sp.send(params.destinationAddress, sp.balance)

    # Rescue FA1.2 Tokens
    @sp.entry_point
    def rescueFA12(self, params):
      sp.set_type(params, sp.TRecord(
        tokenContractAddress = sp.TAddress,
        amount = sp.TNat,
        destination = sp.TAddress,
      ).layout(("tokenContractAddress", ("amount", "destination"))))

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "Not owner")

      # Verify the request is not for the vesting tokens.
      sp.verify(params.tokenContractAddress != self.data.tokenContractAddress, "USE_WITHDRAW_INSTEAD")

      # Transfer the tokens
      handle = sp.contract(
        sp.TRecord(
          from_ = sp.TAddress,
          to_ = sp.TAddress, 
          value = sp.TNat
        ).layout(("from_ as from", ("to_ as to", "value"))),
        params.tokenContractAddress,
        "transfer"
      ).open_some()
      arg = sp.record(from_ = sp.self_address, to_ = params.destination, value = params.amount)
      sp.transfer(arg, sp.mutez(0), handle)

    # Rescue FA2 tokens
    @sp.entry_point
    def rescueFA2(self, params):
      sp.set_type(params, sp.TRecord(
        tokenContractAddress = sp.TAddress,
        tokenId = sp.TNat,
        amount = sp.TNat,
        destination = sp.TAddress,
      ).layout(("tokenContractAddress", ("tokenId", ("amount", "destination")))))

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "Not owner")

      # Verify the request is not for the vesting tokens.
      # The vesting tokens are assumed to be FA1.2 but this sanity check is a trivial amount of gas
      sp.verify(params.tokenContractAddress != self.data.tokenContractAddress, "USE_WITHDRAW_INSTEAD")

      # Transfer the tokens
      handle = sp.contract(
        sp.TList(
          sp.TRecord(
            from_ = sp.TAddress,
            txs = sp.TList(
              sp.TRecord(
                amount = sp.TNat,
                to_ = sp.TAddress, 
                token_id = sp.TNat,
              ).layout(("to_", ("token_id", "amount")))
            )
          ).layout(("from_", "txs"))
        ),
        params.tokenContractAddress,
        "transfer"
      ).open_some()

      arg = [
        sp.record(
          from_ = sp.self_address,
          txs = [
            sp.record(
              amount = params.amount,
              to_ = params.destination,
              token_id = params.tokenId
            )
          ]
        )
      ]
      sp.transfer(arg, sp.mutez(0), handle)

    ################################################################
    # Governance
    ################################################################

    # Rotate the owner key
    @sp.entry_point	
    def rotateOwner(self, params):
      sp.set_type(params, sp.TRecord(newOwner = sp.TAddress).layout("newOwner"))

      # Verify the requester is the governor
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

      # Set owner.
      self.data.owner = params.newOwner  

    # Set a different dao address
    @sp.entry_point	
    def setDaoContractAddress(self, params):
      sp.set_type(params, sp.TRecord(newDaoContractAddress = sp.TAddress).layout("newDaoContractAddress"))

      # Verify the requester is the governor
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

      # Set address.
      self.data.daoContractAddress = params.newDaoContractAddress        

    # Rotate the governor. 
    @sp.entry_point
    def setGovernorContract(self, newGovernorAddress):
      sp.set_type(newGovernorAddress, sp.TAddress)

      # Verify command came from governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

      # Rotate addresses
      self.data.governorAddress = newGovernorAddress

    ################################################################
    # DAO Interactions
    ################################################################

    # Propose a proposal.
    # Params:
    # - escrowAmount (nat): The amount of tokens required to escrow for the proposal.
    # - proposal (Proposal.PROPOSAL_TYPE): The proposal to make
    @sp.entry_point
    def propose(self, params):
      sp.set_type(params, sp.TRecord(
        escrowAmount = sp.TNat,
        proposal = Proposal.PROPOSAL_TYPE
      ).layout(("escrowAmount", "proposal")))

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "Not owner")      

      # Send approvals.
      # This function sends two changes:
      # (1) An approval to 0, in case approval isn't 0 (you can't change an approval from 10 -> 20, you must go 10 -> 0 -> 20)
      # (2) An approval to the requested amount
      approvalHandle = sp.contract(
        sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")),
        self.data.tokenContractAddress,
        "approve"
      ).open_some()

      zeroApprovalArg = sp.record(
        spender = self.data.daoContractAddress,
        value = sp.nat(0)
      )
      sp.transfer(zeroApprovalArg, sp.mutez(0), approvalHandle)

      escrowApprovalArg = sp.record(
        spender = self.data.daoContractAddress, 
        value = params.escrowAmount,
      )
      sp.transfer(escrowApprovalArg, sp.mutez(0), approvalHandle)

      # Send a proposal request
      proposalHandle = sp.contract(
        Proposal.PROPOSAL_TYPE,
        self.data.daoContractAddress,
        "propose"
      ).open_some()
      proposalArg = params.proposal
      sp.transfer(proposalArg, sp.mutez(0), proposalHandle)

    # Vote for a proposal.
    @sp.entry_point
    def vote(self, voteValue):
      sp.set_type(voteValue, sp.TNat)

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "NOT_GOVERNOR")

      # Send a vote request
      handle = sp.contract(
        sp.TNat,
        self.data.daoContractAddress,
        "vote"
      ).open_some()
      sp.transfer(voteValue, sp.mutez(0), handle)

    # Execute a proposal
    @sp.entry_point
    def executeTimelock(self, unit):
      sp.set_type(unit, sp.TUnit)

      # Verify the requester is the owner.
      sp.verify(sp.sender == self.data.owner, "NOT_GOVERNOR")            

      # Send an execution request
      handle = sp.contract(
        sp.TUnit,
        self.data.daoContractAddress,
        "executeTimelock"
      ).open_some()
      sp.transfer(sp.unit, sp.mutez(0), handle)

################################################################
################################################################
# Tests
################################################################
################################################################

# Only run tests if this file is main.
if __name__ == "__main__":

  Dao = sp.import_script_from_url("file:./dao.py")
  Dummy = sp.import_script_from_url("file:./test-helpers/dummy.py")
  FA12 = sp.import_script_from_url("file:./test-helpers/fa12.py")
  FA2 = sp.import_script_from_url("file:./test-helpers/fa2.py")
  Store = sp.import_script_from_url("file:test-helpers/store.py")
  Token = sp.import_script_from_url("file:./token.py")
  VoteValue = sp.import_script_from_url("file:common/vote-value.py")

  ################################################################
  # rescueFA2
  ################################################################

  @sp.add_test(name="rescue FA2 - rescues tokens")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract which is vesting
    config = FA2.FA2_config()
    vestingToken = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += vestingToken

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      tokenContractAddress = vestingToken.address,
      owner = owner,
    )
    scenario += vault

    # AND an extra token contract which is unrelated
    extraToken = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += extraToken

    # AND the vault has extra tokens allocated to it.
    value = sp.nat(100)
    tokenId = 0
    scenario += extraToken.mint(    
      address = vault.address,
      amount = value,
      metadata = FA2.FA2.make_metadata(
        name = "SomeToken",
        decimals = 18,
        symbol= "ST"
      ),
      token_id = tokenId
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )
    
    # WHEN rescueFA2 is called with the extra token.
    scenario += vault.rescueFA2(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenId = tokenId,
        tokenContractAddress = extraToken.address
      )
    ).run(
      sender = owner,
    )    

    # THEN the tokens are rescued.
    scenario.verify(extraToken.data.ledger[(vault.address, tokenId)].balance == sp.nat(0))
    scenario.verify(extraToken.data.ledger[(Addresses.ALICE_ADDRESS, tokenId)].balance == value)

  @sp.add_test(name="rescue FA2 - fails if trying to rescue vesting token")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract which is vesting
    config = FA2.FA2_config()
    vestingToken = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += vestingToken

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      tokenContractAddress = vestingToken.address,
      owner = owner,
    )
    scenario += vault

    # AND an extra token contract which is unrelated
    extraToken = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += extraToken

    # AND the vault has extra tokens allocated to it.
    value = sp.nat(100)
    tokenId = 0
    scenario += extraToken.mint(    
      address = vault.address,
      amount = value,
      metadata = FA2.FA2.make_metadata(
        name = "SomeToken",
        decimals = 18,
        symbol= "ST"
      ),
      token_id = tokenId
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )
    
    # WHEN rescueFA2 is called with the vesting token
    # THEN the call fails
    scenario += vault.rescueFA2(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenId = tokenId,
        tokenContractAddress = vestingToken.address
      )
    ).run(
      sender = owner,
      valid = False
    )    

  @sp.add_test(name="rescue FA2 - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract which is vesting
    config = FA2.FA2_config()
    vestingToken = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += vestingToken

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      tokenContractAddress = vestingToken.address,
      owner = owner,
    )
    scenario += vault

    # AND an extra token contract which is unrelated
    extraToken = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += extraToken

    # AND the vault has extra tokens allocated to it.
    value = sp.nat(100)
    tokenId = 0
    scenario += extraToken.mint(    
      address = vault.address,
      amount = value,
      metadata = FA2.FA2.make_metadata(
        name = "SomeToken",
        decimals = 18,
        symbol= "ST"
      ),
      token_id = tokenId
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )
    
    # WHEN rescueFA2 is called by someone other than the owner
    # THEN the call fails
    notOwner = Addresses.NULL_ADDRESS
    scenario += vault.rescueFA2(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenId = tokenId,
        tokenContractAddress = extraToken.address
      )
    ).run(
      sender = notOwner,
      valid = False
    )    

  ################################################################
  # rescueFA12
  ################################################################

  @sp.add_test(name="rescueFA12 - rescues tokens")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract which is vesting
    vestingToken = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += vestingToken

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      tokenContractAddress = vestingToken.address,
      owner = owner,
    )
    scenario += vault

    # AND an extra token contract which is unrelated
    extraToken = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += extraToken

    # AND the vault has extra tokens allocated to it.
    value = sp.nat(100)
    scenario += extraToken.mint(
      sp.record(
        address = vault.address,
        value = value
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN rescueFA12 is called with the extra token.
    scenario += vault.rescueFA12(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenContractAddress = extraToken.address
      )
    ).run(
      sender = owner,
    )    

    # THEN the tokens are rescued.
    scenario.verify(extraToken.data.balances[vault.address].balance == sp.nat(0))
    scenario.verify(extraToken.data.balances[Addresses.ALICE_ADDRESS].balance == value)

  @sp.add_test(name="rescueFA12 - fails if trying to rescue vesting token")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract which is vesting
    vestingToken = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += vestingToken

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      tokenContractAddress = vestingToken.address,
      owner = owner,
    )
    scenario += vault

    # AND an extra token contract which is unrelated
    extraToken = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += extraToken

    # AND the vault has extra tokens allocated to it.
    value = sp.nat(100)
    scenario += extraToken.mint(
      sp.record(
        address = vault.address,
        value = value
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN rescueFA12 is called with the vesting token
    # THEN the call fails.
    scenario += vault.rescueFA12(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenContractAddress = vestingToken.address
      )
    ).run(
      sender = owner,
      valid = False
    )    

  @sp.add_test(name="rescueFA12 - fails to rescue if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract which is vesting
    vestingToken = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += vestingToken

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      tokenContractAddress = vestingToken.address,
      owner = owner,
    )
    scenario += vault

    # AND an extra token contract which is unrelated
    extraToken = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += extraToken

    # AND the vault has extra tokens allocated to it.
    value = sp.nat(100)
    scenario += extraToken.mint(
      sp.record(
        address = vault.address,
        value = value
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN rescueFA12 is called by someone other than the owner.
    # THEN the call fails
    notOwner = Addresses.NULL_ADDRESS
    scenario += vault.rescueFA12(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenContractAddress = extraToken.address
      )
    ).run(
      sender = notOwner,
      valid = False
    )    

  ################################################################
  # rescueXTZ
  ################################################################

  @sp.add_test(name="rescueXTZ - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      owner = owner,
    )

    # AND the contract has some XTZ
    xtzAmount = sp.tez(10)
    vault.set_initial_balance(xtzAmount)
    scenario += vault

    # WHEN rescue XTZ is called by someone other than the owner.
    # THEN the call fails.
    notOwner = Addresses.NULL_ADDRESS
    scenario += vault.rescueXTZ(
      sp.record(
        destinationAddress = Addresses.ALICE_ADDRESS
      )
    ).run(
      sender = notOwner,
      valid = False
    )

  @sp.add_test(name="rescueXTZ - rescues XTZ")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a vesting vault contract
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      owner = owner,
    )

    # AND the contract has some XTZ
    xtzAmount = sp.tez(10)
    vault.set_initial_balance(xtzAmount)
    scenario += vault

    # AND a dummy contract that will receive the XTZ
    dummy = Dummy.DummyContract()
    scenario += dummy

    # WHEN rescue XTZ is called
    scenario += vault.rescueXTZ(
      sp.record(
        destinationAddress = dummy.address
      )
    ).run(
      sender = owner,
    )

    # THEN XTZ is transferred.
    scenario.verify(vault.balance == sp.tez(0))
    scenario.verify(dummy.balance == xtzAmount)


  ################################################################
  # propose
  ################################################################

  @sp.add_test(name="propose - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a dao contract
    dao = Dao.DaoContract(
      tokenContractAddress = token.address,
    )
    scenario += dao

    # AND a vesting vault contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      daoContractAddress = dao.address,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS,
      level = 0
    )

    # AND a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = 0, admin = dao.address)
    scenario += storeContract

    # AND a proposal
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
    
    # WHEN propose is called by someone other than the owner
    # THEN the call fails.
    notOwner = Addresses.NULL_ADDRESS
    escrowAmount = dao.data.governanceParameters.escrowAmount
    level = 1      
    scenario += vault.propose(
      sp.record(escrowAmount = escrowAmount, proposal = proposal)
    ).run(
      sender = notOwner,
      level = level,
      valid = False
    )

  @sp.add_test(name="propose - can propose")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a dao contract
    dao = Dao.DaoContract(
      tokenContractAddress = token.address,
    )
    scenario += dao

    # AND a vesting vault contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      daoContractAddress = dao.address,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS,
      level = 0
    )

    # AND a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = 0, admin = dao.address)
    scenario += storeContract

    # AND a proposal
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
    
    # WHEN propose is called
    level = 1      
    escrowAmount = dao.data.governanceParameters.escrowAmount
    scenario += vault.propose(
      sp.record(escrowAmount = escrowAmount, proposal = proposal)
    ).run(
      sender = owner,
      level = level,
    )

    # THEN a proposal is loaded into the timelock.
    scenario.verify(dao.data.poll.is_some())

  @sp.add_test(name="propose - can propose when there is a dangling allowance")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a dao contract
    dao = Dao.DaoContract(
      tokenContractAddress = token.address,
    )
    scenario += dao

    # AND a vesting vault contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      daoContractAddress = dao.address,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS,
      level = 0
    )

    # AND a store value contract with the dao as the admin.
    storeContract = Store.StoreValueContract(value = 0, admin = dao.address)
    scenario += storeContract

    # AND a proposal
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

    # AND there is a dangling proposal amount for the dao to move the vault's tokens.
    scenario += token.approve(
      sp.record(
        spender = dao.address,
        value = sp.nat(1),
      )
    ).run(
      sender = dao.address
    )
    
    # WHEN propose is called
    level = 1      
    escrowAmount = dao.data.governanceParameters.escrowAmount
    scenario += vault.propose(
      sp.record(escrowAmount = escrowAmount, proposal = proposal)
    ).run(
      sender = owner,
      level = level,
    )

    # THEN a proposal is loaded into the timelock.
    scenario.verify(dao.data.poll.is_some())

  ################################################################
  # vote
  ################################################################

  @sp.add_test(name="vote - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token

    # AND a poll
    votingEndBlock = sp.nat(21)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = 'abc123',
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
      escrowAmount = sp.nat(1),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    # AND a dao contract with the poll underway.
    dao = Dao.DaoContract(
      poll = sp.some(poll),
      tokenContractAddress = token.address,
    )
    scenario += dao

    # AND a vesting vault contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      daoContractAddress = dao.address,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS,
      level = 0
    )

    # WHEN vote is called by someone other than the owner
    # THEN the call fails.
    notOwner = Addresses.NULL_ADDRESS
    voteValue = VoteValue.YAY
    scenario += vault.vote(voteValue).run(
      sender = notOwner,
      level = sp.as_nat(votingEndBlock - 1),
      valid = False
    )

  @sp.add_test(name="vote - successfully votes")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token

    # AND a poll
    votingEndBlock = sp.nat(21)
    poll = sp.record(
      id = sp.nat(0),
      proposal = sp.record(
        title = 'timelocked prop',
        descriptionLink = 'ipfs://xyz',
        descriptionHash = 'abc123',
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
      escrowAmount = sp.nat(1),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(1), upper = sp.nat(99))
    )

    # AND a dao contract with the poll underway.
    dao = Dao.DaoContract(
      poll = sp.some(poll),
      tokenContractAddress = token.address,
    )
    scenario += dao
    
    # AND a vesting vault contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      daoContractAddress = dao.address,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    tokensInVault = sp.nat(100)
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = tokensInVault
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS,
      level = 0
    )

    # WHEN vote is called
    voteValue = VoteValue.YAY
    scenario += vault.vote(voteValue).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.as_nat(votingEndBlock - 1),
    )    

    # THEN the poll increments the value.
    scenario.verify(dao.data.poll.open_some().yayVotes == tokensInVault)
    scenario.verify(dao.data.poll.open_some().totalVotes == tokensInVault)

    # AND the vesting contract is listed in voters
    scenario.verify(dao.data.poll.open_some().voters.contains(vault.address))

  ################################################################
  # executeTimelock
  ################################################################

  @sp.add_test(name="executeTimelock - successfully executes a proposal")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token

    # AND a vesting vault contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      daoContractAddress = Addresses.DAO_ADDRESS, # Updated later
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND a store value contract with the dao as the admin.
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
      author = vault.address,
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
      author = vault.address,
      escrowAmount = sp.nat(2),
      quorum = sp.nat(100),
      quorumCap = sp.record(lower = sp.nat(0), upper = sp.nat(1000))
    )

    # AND a dao contract with the item.
    dao = Dao.DaoContract(
      timelockItem = sp.some(timelockItem),
      outcomes = sp.big_map(
        l = {
            pollId: sp.record(
              outcome = POLL_OUTCOME_IN_TIMELOCK,
              poll = poll
            )
        },
        tkey = sp.TNat,
        tvalue = HISTORICAL_OUTCOME_TYPE,
      )
    )
    scenario += dao

    # AND the store contract has the dao as the admin.
    scenario += storeContract.setAdmin(dao.address)

    # AND the vault is set to point at the DAO
    setDaoParam = sp.record(newDaoContractAddress = dao.address)
    scenario += vault.setDaoContractAddress(setDaoParam).run(
      sender = Addresses.GOVERNOR_ADDRESS
    )

    # AND the vault is funded.
    tokensInVault = sp.nat(100)
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = tokensInVault
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS,
      level = 0
    )

    # WHEN executeTimelock is called
    scenario += vault.executeTimelock(sp.unit).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = endBlock + 1,
    )    

    # THEN the proposal executed
    scenario.verify(storeContract.data.storedValue == newValue)

    # AND the historical outcome is updated.
    scenario.verify(dao.data.outcomes[pollId].outcome == POLL_OUTCOME_EXECUTED)

    # AND the timelock is empty.
    scenario.verify(~dao.data.timelockItem.is_some())

  ################################################################
  # rotateOwner
  ################################################################

  @sp.add_test(name="rotateOwner - fails if not called by governor")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      tokenContractAddress = token.address
    )
    scenario += vault

    # WHEN rotateOwner is called by someone other than the governor
    # THEN the call fails.
    notGovernor = Addresses.NULL_ADDRESS
    scenario += vault.rotateOwner(
      sp.record(
        newOwner = Addresses.ROTATED_ADDRESS
      )
    ).run(
      sender = notGovernor,
      valid = False
    )

  @sp.add_test(name="rotateOwner - can rotate owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      tokenContractAddress = token.address
    )
    scenario += vault

    # WHEN rotateOwner is called by the governor
    scenario += vault.rotateOwner(
      sp.record(
        newOwner = Addresses.ROTATED_ADDRESS
      )
    ).run(
      sender = Addresses.GOVERNOR_ADDRESS
    )    

    # THEN the owner address is updated.
    scenario.verify(vault.data.owner == Addresses.ROTATED_ADDRESS)

  ################################################################
  # setDaoContractAddress
  ################################################################

  @sp.add_test(name="setDaoContractAddress - fails if not called by governor")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      tokenContractAddress = token.address
    )
    scenario += vault

    # WHEN setDaoContractAddress is called by someone other than the governor
    # THEN the call fails.
    notGovernor = Addresses.NULL_ADDRESS
    scenario += vault.setDaoContractAddress(
      sp.record(
        newDaoContractAddress = Addresses.ROTATED_ADDRESS
      )
    ).run(
      sender =  notGovernor,
      valid = False
    )

  @sp.add_test(name="setDaoContractAddress - can change dao address")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      tokenContractAddress = token.address
    )
    scenario += vault

    # WHEN setDaoContractAddress is called by the governor
    scenario += vault.setDaoContractAddress(
      sp.record(
        newDaoContractAddress = Addresses.ROTATED_ADDRESS
      )
    ).run(
      sender = Addresses.GOVERNOR_ADDRESS
    )    

    # THEN the dao address is updated.
    scenario.verify(vault.data.daoContractAddress == Addresses.ROTATED_ADDRESS)

  ################################################################
  # withdraw
  ################################################################

  @sp.add_test(name="withdraw - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called by someone other than the owner
    # THEN the call fails.
    notOwner = Addresses.NULL_ADDRESS
    numberOfBlocks = sp.nat(2)
    level = startBlock + numberOfBlocks
    withdrawAmount = sp.as_nat(level - startBlock) * amountPerBlock
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = withdrawAmount
      )
    ).run(
      sender = notOwner,
      level = level,
      valid = False
    )

  @sp.add_test(name="withdraw - fails if withdraw amount is over limit")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called for one more token than is available
    # THEN the call fails.
    numberOfBlocks = sp.nat(1)
    level = startBlock + numberOfBlocks
    withdrawAmount = (sp.as_nat(level - startBlock) * amountPerBlock) + 1
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = withdrawAmount
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = level,
      valid = False
    )    

  @sp.add_test(name="withdraw - can withdraw exactly the vested amount over one period")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called for the exact amount in two blocks.
    numberOfBlocks = sp.nat(2)
    level = startBlock + numberOfBlocks
    withdrawAmount = sp.as_nat(level - startBlock) * amountPerBlock
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = withdrawAmount
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = level
    )

    # THEN the recipient received the tokens.
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == withdrawAmount)

    # AND the amountWithdrawn is updated correctly.
    scenario.verify(vault.data.amountWithdrawn == withdrawAmount)

  @sp.add_test(name="withdraw - can withdraw exactly the vested amount in two transactions in the same block")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called for the exact amount in two transactions
    numberOfBlocks = sp.nat(2)
    level = startBlock + numberOfBlocks
    withdrawAmount = (sp.as_nat(level - startBlock) * amountPerBlock) // 2
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = withdrawAmount
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = level
    )
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = withdrawAmount
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = level
    )

    # THEN the recipient received the tokens.
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == sp.nat(2))

    # AND the amountWithdrawn is updated correctly.
    scenario.verify(vault.data.amountWithdrawn == sp.nat(2)) 
  
  @sp.add_test(name="withdraw - can withdraw exactly the vested amount in two transactions in different blocks")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called for the exact amount in two transactions in two blocks

    # limit = 2, total withdrawn = 0, requested = 1
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = sp.nat(1)
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.nat(2)
    )

    # limit = 3, total withdrawn = 1, requested = 2
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = sp.nat(2)
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.nat(3)
    )

    # THEN the recipient received the tokens.
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == sp.nat(3))

    # AND the amountWithdrawn is updated correctly.
    scenario.verify(vault.data.amountWithdrawn == sp.nat(3)) 

  @sp.add_test(name="withdraw - can withdraw exactly the vested amount with a different start block")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract starting from a block which is not zero
    amountPerBlock = 1
    startBlock = 2 # not zero
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called for the exact amount in two blocks.
    numberOfBlocks = sp.nat(2)
    level = startBlock + numberOfBlocks
    withdrawAmount = sp.as_nat(level - startBlock) * amountPerBlock
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = withdrawAmount
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = level
    )

    # THEN the recipient received the tokens.
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == withdrawAmount)    

    # AND the amountWithdrawn is updated correctly.
    scenario.verify(vault.data.amountWithdrawn == withdrawAmount)   

  @sp.add_test(name="withdraw - correctly tabulates multiple transactions")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a vesting contract
    amountPerBlock = 1
    startBlock = 0
    owner = Addresses.TOKEN_RECIPIENT
    vault = VestingVault(
      amountPerBlock = amountPerBlock,
      startBlock = startBlock,
      owner = owner,
      tokenContractAddress = token.address
    )
    scenario += vault

    # AND the vault is funded.
    scenario += token.mint(
      sp.record(
        address = vault.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN withdraw is called twice with amount under the limit, both will succeed.

    # limit = 2, total withdrawn = 0, requested = 1
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = sp.nat(1)
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.nat(2)
    )

    # limit = 3, total withdrawn = 1, requested = 1
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = sp.nat(1)
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.nat(3)
    )

    # AND a withdrawal that goes over the limit will fail

    # limit = 4, total withdrawn = 2, requested = 3
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = sp.nat(3)
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.nat(4),
      valid = False
    )

    # AND a withdraw to exactly the limit will succeed

    # limit = 4, total withdrawn = 2, requested = 2
    scenario += vault.withdraw(
      sp.record(
        numberOfTokens = sp.nat(2)
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      level = sp.nat(4),
    )

    # THEN the recipient received the tokens.
    expectedAmount = sp.nat(1 + 1 + 2) # Two 1 token and one 2 token withdrawals were processsed
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == expectedAmount)

    # AND the amountWithdrawn is updated correctly.
    scenario.verify(vault.data.amountWithdrawn == expectedAmount)    

  ################################################################
  # setGovernorContract
  ################################################################

  @sp.add_test(name="setGovernorContract - can rotate governor")
  def test():
    # GIVEN a Vesting Vault with an governor
    scenario = sp.test_scenario()

    vault = VestingVault(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += vault

    # WHEN setGovernorContract is called by the governor
    scenario += vault.setGovernorContract(Addresses.ROTATED_ADDRESS).run(
      sender = Addresses.GOVERNOR_ADDRESS,
    )

    # THEN the governor is rotated.
    scenario.verify(vault.data.governorAddress == Addresses.ROTATED_ADDRESS)

  @sp.add_test(name="setGovernorContract - fails when not called by governor")
  def test():
    # GIVEN a Vesting Vault with an governor
    scenario = sp.test_scenario()

    vault = VestingVault(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += vault

    # WHEN setGovernorContract is called by someone other than the governor THEN the invocation fails.
    notGovernor = Addresses.NULL_ADDRESS
    scenario += vault.setGovernorContract(Addresses.ROTATED_ADDRESS).run(
      sender = notGovernor,
      valid = False
    )


  sp.add_compilation_target("vesting-vault", VestingVault())

