import smartpy as sp

################################################################
################################################################
# Contract
################################################################
################################################################

Addresses = sp.import_script_from_url("file:./test-helpers/addresses.py")

# A community fund for KOL tokens managed by the DAO.
class CommunityFund(sp.Contract):
    def __init__(
      self, 
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      governorAddress = Addresses.GOVERNOR_ADDRESS
    ):
        metadata_data = sp.bytes_of_string('{ "name": "Kolibri DAO Community Fund", "description": "Governance Token Fund for Kolibri DAO", "authors": ["Hover Labs <hello@hover.engineering>"], "homepage":  "https://kolibri.finance" }')

        metadata = sp.big_map(
            l = {
                "": sp.bytes('0x74657a6f732d73746f726167653a64617461'), # "tezos-storage:data"
                "data": metadata_data
            },
          tkey = sp.TString,
            tvalue = sp.TBytes            
        )

        self.init(
          # The address of the token contract.
          tokenContractAddress = tokenContractAddress,
          # The governor address
          governorAddress = governorAddress,
          # Contract metadata.
          metadata = metadata,
        )

    @sp.entry_point
    def default(self):
      pass        

    # Rotate the governor. 
    @sp.entry_point
    def setGovernorContract(self, newGovernorAddress):
      sp.set_type(newGovernorAddress, sp.TAddress)

      # Verify command came from governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

      # Rotate addresses
      self.data.governorAddress = newGovernorAddress

    # Send tokens.
    @sp.entry_point	
    def send(self, params):
      sp.set_type(params, sp.TRecord(numberOfTokens = sp.TNat, destination = sp.TAddress).layout(("numberOfTokens", "destination")))

      # Verify command came from governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

      # Request tokens transferred to destination
      handle = sp.contract(
        sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
        self.data.tokenContractAddress,
        "transfer"
      ).open_some()
      arg = sp.record(from_ = sp.self_address, to_ = params.destination, value = params.numberOfTokens)
      sp.transfer(arg, sp.mutez(0), handle)

    # Rescue XTZ
    @sp.entry_point	
    def rescueXTZ(self, params):
      sp.set_type(params, sp.TRecord(destinationAddress = sp.TAddress).layout("destinationAddress"))

      # Verify the requester is the governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")
      sp.send(params.destinationAddress, sp.balance)

    # Rescue FA1.2 Tokens
    @sp.entry_point
    def rescueFA12(self, params):
      sp.set_type(params, sp.TRecord(
        tokenContractAddress = sp.TAddress,
        amount = sp.TNat,
        destination = sp.TAddress,
      ).layout(("tokenContractAddress", ("amount", "destination"))))

      # Verify the requester is the governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

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

      # Verify the requester is the governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

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

    @sp.entry_point
    def setDelegate(self, newDelegate):
      sp.set_type(newDelegate, sp.TOption(sp.TKeyHash))

      # Verify the caller is the governor.
      sp.verify(sp.sender == self.data.governorAddress, "NOT_GOVERNOR")

      sp.set_delegate(newDelegate)

################################################################
################################################################
# Tests
################################################################
################################################################

# Only run tests if this file is main.
if __name__ == "__main__":
  
  Dummy = sp.import_script_from_url("file:./test-helpers/dummy.py")
  FA12 = sp.import_script_from_url("file:./test-helpers/fa12.py")
  FA2 = sp.import_script_from_url("file:./test-helpers/fa2.py")
  Token = sp.import_script_from_url("file:./token.py")

  ################################################################
  # Set Delegate
  ################################################################

  @sp.add_test(name="setDelegate - fails with bad owner")
  def test():
    # GIVEN a fund contract
    scenario = sp.test_scenario()

    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += fund

    # WHEN setDelegate is called by someone other than the governor
    # THEN the invocation fails.
    notGovernor = Addresses.NULL_ADDRESS
    delegate = sp.some(sp.key_hash("tz1abmz7jiCV2GH2u81LRrGgAFFgvQgiDiaf"))
    scenario += fund.setDelegate(delegate).run(
        sender = notGovernor,
        valid = False
    )

  @sp.add_test(name="setDelegate - updates delegate")
  def test():
    # GIVEN a fund contract
    scenario = sp.test_scenario()

    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += fund

    # WHEN setDelegate is called by the administrator
    delegate = sp.some(sp.key_hash("tz1abmz7jiCV2GH2u81LRrGgAFFgvQgiDiaf"))
    scenario += fund.setDelegate(delegate).run(
      sender = Addresses.GOVERNOR_ADDRESS,
    )

    # THEN the delegate is updated.
    scenario.verify(fund.baker.open_some() == delegate.open_some())

  ################################################################
  # rescueFA2
  ################################################################

  @sp.add_test(name="rescue FA2 - rescues tokens")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    config = FA2.FA2_config()
    token = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += token

    # GIVEN a community fund contract
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += fund

    # AND the fund has extra tokens allocated to it.
    value = sp.nat(100)
    tokenId = 0
    scenario += token.mint(    
      address = fund.address,
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
    scenario += fund.rescueFA2(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenId = tokenId,
        tokenContractAddress = token.address
      )
    ).run(
      sender = Addresses.GOVERNOR_ADDRESS,
    )    

    # THEN the tokens are rescued.
    scenario.verify(token.data.ledger[(fund.address, tokenId)].balance == sp.nat(0))
    scenario.verify(token.data.ledger[(Addresses.ALICE_ADDRESS, tokenId)].balance == value)

  @sp.add_test(name="rescue FA2 - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    config = FA2.FA2_config()
    token = FA2.FA2(
      config = config,
      metadata = sp.metadata_of_url("https://example.com"),      
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += token

    # GIVEN a community fund contract
    owner = Addresses.TOKEN_RECIPIENT
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += fund

    # AND the fund has extra tokens allocated to it.
    value = sp.nat(100)
    tokenId = 0
    scenario += token.mint(    
      address = fund.address,
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
    
    # WHEN rescueFA2 is called by someone other than the governor
    # THEN the call fails
    notGovernor = Addresses.NULL_ADDRESS
    scenario += fund.rescueFA2(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenId = tokenId,
        tokenContractAddress = token.address
      )
    ).run(
      sender = notGovernor,
      valid = False
    )    

  ################################################################
  # rescueFA12
  ################################################################

  @sp.add_test(name="rescueFA12 - rescues tokens")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += token

    # GIVEN a community fund contract
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS,
    )
    scenario += fund

    # AND the fund has extra tokens allocated to it.
    value = sp.nat(100)
    scenario += token.mint(
      sp.record(
        address = fund.address,
        value = value
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN rescueFA12 is called with the extra token.
    scenario += fund.rescueFA12(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenContractAddress = token.address
      )
    ).run(
      sender = Addresses.GOVERNOR_ADDRESS,
    )    

    # THEN the tokens are rescued.
    scenario.verify(token.data.balances[fund.address].balance == sp.nat(0))
    scenario.verify(token.data.balances[Addresses.ALICE_ADDRESS].balance == value)

  @sp.add_test(name="rescueFA12 - fails to rescue if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = FA12.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS
    )
    scenario += token

    # GIVEN a community fund contract
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS,
    )
    scenario += fund

    # AND the fund has extra tokens allocated to it.
    value = sp.nat(100)
    scenario += token.mint(
      sp.record(
        address = fund.address,
        value = value
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN rescueFA12 is called by someone other than the governor.
    # THEN the call fails
    notGovernor = Addresses.NULL_ADDRESS
    scenario += fund.rescueFA12(
      sp.record(
        destination = Addresses.ALICE_ADDRESS,
        amount = value,
        tokenContractAddress = token.address
      )
    ).run(
      sender = notGovernor,
      valid = False
    )    

  ################################################################
  # rescueXTZ
  ################################################################

  @sp.add_test(name="rescueXTZ - fails if not called by owner")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a community fund contract
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS,
    )

    # AND the contract has some XTZ
    xtzAmount = sp.tez(10)
    fund.set_initial_balance(xtzAmount)
    scenario += fund

    # WHEN rescue XTZ is called by someone other than the governor.
    # THEN the call fails.
    notGovernor = Addresses.NULL_ADDRESS
    scenario += fund.rescueXTZ(
      sp.record(
        destinationAddress = Addresses.ALICE_ADDRESS
      )
    ).run(
      sender = notGovernor,
      valid = False
    )

  @sp.add_test(name="rescueXTZ - rescues XTZ")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a community fund contract
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS,
    )

    # AND the contract has some XTZ
    xtzAmount = sp.tez(10)
    fund.set_initial_balance(xtzAmount)
    scenario += fund

    # AND a dummy contract that will receive the XTZ
    dummy = Dummy.DummyContract()
    scenario += dummy

    # WHEN rescue XTZ is called
    scenario += fund.rescueXTZ(
      sp.record(
        destinationAddress = dummy.address
      )
    ).run(
      sender = Addresses.GOVERNOR_ADDRESS,
    )

    # THEN XTZ is transferred.
    scenario.verify(fund.balance == sp.tez(0))
    scenario.verify(dummy.balance == xtzAmount)

  ################################################################
  # sendTokens
  ################################################################

  @sp.add_test(name="send - can move funds")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a community fund contract with an governor
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      tokenContractAddress = token.address
    )
    scenario += fund

    # AND the fund is funded.
    scenario += token.mint(
      sp.record(
        address = fund.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN funds are sent to a recipient from the governor.
    numberOfTokens = 42
    scenario += fund.send(
      sp.record(
        numberOfTokens = numberOfTokens,
        destination = Addresses.TOKEN_RECIPIENT
      )
    ).run(
      sender = Addresses.GOVERNOR_ADDRESS
    )

    # THEN the recipient received the tokens.
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == numberOfTokens)

  @sp.add_test(name="send - fails if not called by governor")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a community fund contract
    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS,
      tokenContractAddress = token.address
    )
    scenario += fund

    # AND the fund is funded.
    scenario += token.mint(
      sp.record(
        address = fund.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN funds are sent to a recipient from someone other than the governor
    # THEN the call fails.
    numberOfTokens = 42
    notGovernor = Addresses.NULL_ADDRESS
    scenario += fund.send(
      sp.record(
        numberOfTokens = numberOfTokens,
        destination = Addresses.TOKEN_RECIPIENT
      )
    ).run(
      sender = notGovernor,
      valid = False
    )

  ################################################################
  # setGovernorContract
  ################################################################

  @sp.add_test(name="setGovernorContract - can rotate governor")
  def test():
    # GIVEN a community fund with an governor
    scenario = sp.test_scenario()

    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += fund

    # WHEN setGovernorContract is called by the governor
    scenario += fund.setGovernorContract(Addresses.ROTATED_ADDRESS).run(
      sender = Addresses.GOVERNOR_ADDRESS,
    )

    # THEN the governor is rotated.
    scenario.verify(fund.data.governorAddress == Addresses.ROTATED_ADDRESS)

  @sp.add_test(name="setGovernorContract - fails when not called by governor")
  def test():
    # GIVEN a community fund with an governor
    scenario = sp.test_scenario()

    fund = CommunityFund(
      governorAddress = Addresses.GOVERNOR_ADDRESS
    )
    scenario += fund

    # WHEN setGovernorContract is called by someone other than the governor THEN the invocation fails.
    notGovernor = Addresses.NULL_ADDRESS
    scenario += fund.setGovernorContract(Addresses.ROTATED_ADDRESS).run(
      sender = notGovernor,
      valid = False
    )

  sp.add_compilation_target("community-fund", CommunityFund())

