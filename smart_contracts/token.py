# Fungible Assets - FA12
# Inspired by https://gitlab.com/tzip/tzip/blob/master/A/FA1.2.md

# This file is copied verbatim from http://smartpy.io/dev/?template=fa12.py on 23/02/2021.
# All changed lines are annotated with `CHANGED: <description>`

# This contract is based largely off of Compound's COMP token:
# https://github.com/compound-finance/compound-protocol/blob/master/contracts/Governance/Comp.sol

import smartpy as sp

Addresses = sp.import_script_from_url("file:test-helpers/addresses.py")

# CHANGED: Compress the contract into a single entity, rather than using inheritance.
class FA12(sp.Contract):
    def __init__(
        self, 
        # CHANGED: Give admin a default value
        admin = Addresses.TOKEN_ADMIN_ADDRESS
    ):
        # CHANGED: Construct token metadata.
        token_id = sp.nat(0)
        kol_metadata = sp.map(
            l = {
                "name": sp.bytes_of_string('Kolibri DAO Token'),
                "decimals": sp.bytes('0x3138'), # 18
                "symbol": sp.bytes_of_string('kDAO'),
                "icon": sp.bytes('0x2068747470733a2f2f6b6f6c696272692d646174612e73332e616d617a6f6e6177732e636f6d2f6c6f676f2e706e67') # https://kolibri-data.s3.amazonaws.com/logo.png
            },
            tkey = sp.TString,
            tvalue = sp.TBytes
        )
        token_metadata = sp.big_map(
          {
            0: sp.record(token_id = 0, token_info = kol_metadata)
          },
          tkey = sp.TNat,
          tvalue = sp.TRecord(token_id = sp.TNat, token_info = sp.TMap(sp.TString, sp.TBytes))
        )
        
        metadata_data = sp.bytes_of_string('{ "name": "kDAO Token", "description": "The FA1.2 Governance Token For Kolibri", "authors": ["Hover Labs <hello@hover.engineering>"], "homepage":  "https://kolibri.finance", "interfaces": [ "TZIP-007-2021-01-29"] }')

        metadata = sp.big_map(
            l = {
                "": sp.bytes('0x74657a6f732d73746f726167653a64617461'), # "tezos-storage:data"
                "data": metadata_data
            },
            tkey = sp.TString,
            tvalue = sp.TBytes            
        )


        self.init(
            balances = sp.big_map(
                tvalue = sp.TRecord(
                    approvals = sp.TMap(sp.TAddress, sp.TNat), 
                    balance = sp.TNat
                )
            ),
            # CHANGED: Add Checkpoints
            checkpoints = sp.big_map(
                l = {},
                tkey = sp.TAddress,
                tvalue = sp.TMap(
                    sp.TNat, 
                    sp.TRecord(fromBlock = sp.TNat, balance = sp.TNat).layout(("fromBlock", "balance"))
                )
            ),
            # CHANGED: Add numCheckpoints
            numCheckpoints = sp.big_map(
                l = {},
                tkey = sp.TAddress,
                tvalue = sp.TNat
            ),
            # CHANGED: Allow minting to be disabled.
            mintingDisabled = False,
            # CHANGED: Include metadata and token_metadata bigmap in storage.
            metadata = metadata,
            token_metadata = token_metadata,

            totalSupply = 0, 
            paused = False, 
            # CHANGED: Make administrator an optional.
            administrator = sp.some(admin), 
        )

    # CHANGED: Allow administrator to update contract metadata.	
    @sp.entry_point	
    def updateContractMetadata(self, params):	
        sp.set_type(params, sp.TPair(sp.TString, sp.TBytes))	

        sp.verify(self.is_administrator(sp.sender), "NOT_ADMINISTRATOR")

        key = sp.fst(params)	
        value = sp.snd(params)	
        self.data.metadata[key] = value

    # CHANGED: Allow admin to update token metadata.	
    @sp.entry_point	
    def updateTokenMetadata(self, params):	
        sp.set_type(params, sp.TRecord(token_id = sp.TNat, token_info = sp.TMap(sp.TString, sp.TBytes)))	

        sp.verify(self.is_administrator(sp.sender), "NOT_ADMINISTRATOR")

        self.data.token_metadata[0] = params
        
    # CHANGED: Add method to write checkpoints.
    @sp.sub_entry_point
    def writeCheckpoint(self, params):
        sp.set_type(params, sp.TRecord(checkpointedAddress = sp.TAddress, numCheckpoints = sp.TNat, newBalance = sp.TNat).layout(("checkpointedAddress", ("numCheckpoints", "newBalance"))))

        # If there are no checkpoints, write data.
        sp.if params.numCheckpoints == 0:
            self.data.checkpoints[params.checkpointedAddress] = { 0: sp.record(fromBlock = sp.level, balance = params.newBalance)}
            self.data.numCheckpoints[params.checkpointedAddress] = params.numCheckpoints + 1
        sp.else:
            # Otherwise, if this update occurred in the same block, overwrite
            sp.if self.data.checkpoints[params.checkpointedAddress][sp.as_nat(params.numCheckpoints - 1)].fromBlock == sp.level: 
                self.data.checkpoints[params.checkpointedAddress][sp.as_nat(params.numCheckpoints - 1)] = sp.record(fromBlock = sp.level, balance = params.newBalance)
            sp.else:
                # Only write an additional checkpoint if the balance has changed.
                sp.if self.data.checkpoints[params.checkpointedAddress][sp.as_nat(params.numCheckpoints - 1)].balance != params.newBalance:
                    self.data.checkpoints[params.checkpointedAddress][params.numCheckpoints] = sp.record(fromBlock = sp.level, balance = params.newBalance)
                    self.data.numCheckpoints[params.checkpointedAddress] = params.numCheckpoints + 1
      
    # CHANGED: Add view to get balance from checkpoints
    @sp.view(sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat))
    def getPriorBalance(self, params):
        sp.set_type(params, sp.TRecord(
            address = sp.TAddress,
            level = sp.TNat,
        ).layout(("address", "level")))

        sp.verify(params.level < sp.level, "BLOCK_LEVEL_TOO_SOON")

        # If there are no checkpoints, return 0.
        sp.if self.data.numCheckpoints.get(params.address, 0) == 0:
            sp.result(sp.record(result = 0, address = params.address, level = params.level))
        sp.else:
            # First check most recent balance.
            sp.if self.data.checkpoints[params.address][sp.as_nat(self.data.numCheckpoints[params.address] - 1)].fromBlock <= params.level:
                sp.result(sp.record(
                    result = self.data.checkpoints[params.address][sp.as_nat(self.data.numCheckpoints[params.address] - 1)].balance,
                    address = params.address,
                    level = params.level
                ))
            sp.else:
                # Next, check for an implicit zero balance.
                sp.if self.data.checkpoints[params.address][sp.nat(0)].fromBlock > params.level:
                    sp.result(sp.record(result = 0, address = params.address, level = params.level))
                sp.else:
                    # A boolean that indicates that the current center is the level we are looking for.
                    # This extra variable is required because SmartPy does not have a way to break from
                    # a while loop. 
                    centerIsNeedle = sp.local('centerIsNeedle', False)

                    # Otherwise perform a binary search.
                    center = sp.local('center', 0)
                    lower = sp.local('lower', 0)
                    upper = sp.local('upper', sp.as_nat(self.data.numCheckpoints[params.address] - 1))   
                                        
                    sp.while (upper.value > lower.value) & (centerIsNeedle.value == False):
                        # A complicated way to get the ceiling.
                        center.value = sp.as_nat(upper.value - (sp.as_nat(upper.value - lower.value) / 2))
                        
                        # Check that center is the exact block we are looking for.
                        sp.if self.data.checkpoints[params.address][center.value].fromBlock == params.level:
                            centerIsNeedle.value = True
                        sp.else:
                            sp.if self.data.checkpoints[params.address][center.value].fromBlock < params.level:
                                lower.value = center.value
                            sp.else:
                                upper.value = sp.as_nat(center.value - 1)

                    # If the center is the needle, return the value at center.
                    sp.if centerIsNeedle.value == True:
                        sp.result(
                            sp.record(
                                result = self.data.checkpoints[params.address][center.value].balance,
                                address = params.address, 
                                level = params.level
                            )
                        )
                    # Otherwise return the result.
                    sp.else:
                        sp.result(
                            sp.record(
                                result = self.data.checkpoints[params.address][lower.value].balance, 
                                address = params.address, 
                                level = params.level
                            )
                        )
        
    @sp.entry_point
    def transfer(self, params):
        sp.set_type(params, sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))))
        sp.verify(self.is_administrator(sp.sender) |
            (~self.is_paused() &
                ((params.from_ == sp.sender) |
                 (self.data.balances[params.from_].approvals[sp.sender] >= params.value))), "NOT_ALLOWED")
        self.addAddressIfNecessary(params.to_)

        # CHANGED: Add from address as well.
        self.addAddressIfNecessary(params.from_)

        sp.verify(self.data.balances[params.from_].balance >= params.value, "LOW_BALANCE")
        self.data.balances[params.from_].balance = sp.as_nat(self.data.balances[params.from_].balance - params.value)
        self.data.balances[params.to_].balance += params.value
        sp.if (params.from_ != sp.sender) & (~self.is_administrator(sp.sender)):
            self.data.balances[params.from_].approvals[sp.sender] = sp.as_nat(self.data.balances[params.from_].approvals[sp.sender] - params.value)
            
        # CHANGED: Write checkpoints.
        # Write a checkpoint for the sender.
        self.writeCheckpoint(
            sp.record(
                checkpointedAddress = params.from_,
                numCheckpoints = self.data.numCheckpoints.get(params.from_, 0),
                newBalance = self.data.balances[params.from_].balance
            )
        )
        # Write a checkpoint for the receiver
        self.writeCheckpoint(
            sp.record(
                checkpointedAddress = params.to_,
                numCheckpoints = self.data.numCheckpoints.get(params.to_, 0),
                newBalance = self.data.balances[params.to_].balance
            )
        )

    @sp.entry_point
    def approve(self, params):
        sp.set_type(params, sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")))

        # CHANGED: Add address if needed. This fixes a bug in our tests for checkpoints where you cannot approve
        # before you have a balance.
        self.addAddressIfNecessary(sp.sender)

        sp.verify(~self.is_paused(), "PAUSED")
        alreadyApproved = self.data.balances[sp.sender].approvals.get(params.spender, 0)
        sp.verify((alreadyApproved == 0) | (params.value == 0), "UNSAFE_ALLOWANCE_CHANGE")
        self.data.balances[sp.sender].approvals[params.spender] = params.value

    def addAddressIfNecessary(self, address):
        sp.if ~ self.data.balances.contains(address):
            self.data.balances[address] = sp.record(balance = 0, approvals = {})

    @sp.view(sp.TNat)
    def getBalance(self, params):
        # CHANGED: Add address if needed.
        self.addAddressIfNecessary(params)

        sp.result(self.data.balances[params].balance)

    @sp.view(sp.TNat)
    def getAllowance(self, params):
        # CHANGED: Add address if needed.
        self.addAddressIfNecessary(params.owner)

        sp.result(self.data.balances[params.owner].approvals.get(params.spender, sp.nat(0)))

    @sp.view(sp.TNat)
    def getTotalSupply(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.totalSupply)

    # CHANGED: Allow minting to be disabled.
    @sp.entry_point
    def disableMinting(self, unit):
        sp.set_type(unit, sp.TUnit)

        sp.verify(self.is_administrator(sp.sender), "NOT_ADMINISTRATOR")
        self.data.mintingDisabled = True        

    @sp.entry_point
    def mint(self, params):
        # CHANGED: Disallow minting.
        sp.verify(self.data.mintingDisabled == False, "MINTING_DISABLED")
        
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))
        sp.verify(self.is_administrator(sp.sender), "NOT_ADMINISTRATOR")
        self.addAddressIfNecessary(params.address)
        self.data.balances[params.address].balance += params.value
        self.data.totalSupply += params.value
        
        # CHANGED
        # Write a checkpoint for the receiver
        self.writeCheckpoint(
            sp.record(
                checkpointedAddress = params.address,
                numCheckpoints = self.data.numCheckpoints.get(params.address, 0),
                newBalance = self.data.balances[params.address].balance
            )
        )
        
    # CHANGED: Remove burning.       

    def is_administrator(self, sender):
      return self.data.administrator == sp.some(sender)
      
    @sp.entry_point
    def setAdministrator(self, params):
        sp.set_type(params, sp.TOption(sp.TAddress))
        sp.verify(self.is_administrator(sp.sender), "NOT_ADMINISTRATOR")
        self.data.administrator = params

    @sp.view(sp.TOption(sp.TAddress))
    def getAdministrator(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.administrator)

    def is_paused(self):
        return self.data.paused

    @sp.entry_point
    def setPause(self, params):
        sp.set_type(params, sp.TBool)
        sp.verify(self.is_administrator(sp.sender), "NOT_ADMINISTRATOR")
        self.data.paused = params


class Viewer(sp.Contract):
    def __init__(self, t):
        self.init(last = sp.none)
        self.init_type(sp.TRecord(last = sp.TOption(t)))
    @sp.entry_point
    def target(self, params):
        self.data.last = sp.some(params)

# Only run tests if this file is main.
if __name__ == "__main__":

    Addresses = sp.import_script_from_url("file:./test-helpers/addresses.py")

    ################################################################
    # transfer
    ################################################################

    @sp.add_test(name="transfer - allows transfvers if admin is none")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND an alice has 100 tokens
        scenario += token.mint(
            sp.record(
                value = 100,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = sp.nat(0),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # AND the admin is set to none
        scenario += token.setAdministrator(sp.none).run(
          sender = Addresses.TOKEN_ADMIN_ADDRESS
        )

        # WHEN Alice transfers tokens
        scenario += token.transfer(from_ = Addresses.ALICE_ADDRESS, to_ = Addresses.BOB_ADDRESS, value = 1).run(sender = Addresses.ALICE_ADDRESS)

    ################################################################
    # getPriorBalance
    #
    # These tests are laregely based off of Compound's tests:
    # https://github.com/compound-finance/compound-protocol/blob/master/tests/Governance/CompTest.js
    ################################################################

    @sp.add_test(name="getPriorBalance - reverts if block is not yet finalized")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND a viewer contract.
        viewer = Viewer(
            t = sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat)
        )
        scenario += viewer

        # AND an alice has 100 tokens
        scenario += token.mint(
            sp.record(
                value = 100,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = sp.nat(0),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # WHEN a balance is requested for Alice for the current block
        # THEN the call fails
        level = sp.nat(1)
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.ALICE_ADDRESS,
                    level = level
                ),
                viewer.typed
            )
        ).run(
            level = level,
            valid = False
        )

    @sp.add_test(name="getPriorBalance - returns 0 if there are no checkpoints")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND a viewer contract.
        viewer = Viewer(
            t = sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat)
        )
        scenario += viewer

        # WHEN a balance is requested for Alice, who has no checkpoints
        requestLevel = 2
        currentLevel = sp.nat(14)
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.ALICE_ADDRESS,
                    level = requestLevel
                ),
                viewer.typed
            )
        ).run(
            level = currentLevel,
        )        

        # THEN the correct data is returned.
        scenario.verify(viewer.data.last.open_some().address == Addresses.ALICE_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == requestLevel)
        scenario.verify(viewer.data.last.open_some().result == sp.nat(0))

    @sp.add_test(name="getPriorBalance - returns 0 requested block is before the first checkpoint")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND a viewer contract.
        viewer = Viewer(
            t = sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat)
        )
        scenario += viewer

        # AND an alice has 100 tokens
        firstCheckpointLevel = sp.nat(5)
        scenario += token.mint(
            sp.record(
                value = 100,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = firstCheckpointLevel,
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # WHEN a balance is requested for Alice before her first checkpiont
        requestLevel = sp.as_nat(firstCheckpointLevel - 2)
        currentLevel = firstCheckpointLevel + 2
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.ALICE_ADDRESS,
                    level = requestLevel
                ),
                viewer.typed
            )
        ).run(
            level = currentLevel,
        )        

        # THEN the correct data is returned.
        scenario.verify(viewer.data.last.open_some().address == Addresses.ALICE_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == requestLevel)
        scenario.verify(viewer.data.last.open_some().result == sp.nat(0))

    @sp.add_test(name="getPriorBalance - returns last balance if requested block is after the lasts checkpoint")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND a viewer contract.
        viewer = Viewer(
            t = sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat)
        )
        scenario += viewer

        # AND an alice has 100 tokens
        firstCheckpointLevel = sp.nat(5)
        totalSupply = 100
        scenario += token.mint(
            sp.record(
                value = totalSupply,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = firstCheckpointLevel,
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # WHEN a balance is requested for Alice before her first checkpiont
        requestLevel = firstCheckpointLevel + 2
        currentLevel = firstCheckpointLevel + 4
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.ALICE_ADDRESS,
                    level = requestLevel
                ),
                viewer.typed
            )
        ).run(
            level = currentLevel,
        )        

        # THEN the correct data is returned.
        scenario.verify(viewer.data.last.open_some().address == Addresses.ALICE_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == requestLevel)
        scenario.verify(viewer.data.last.open_some().result == totalSupply)

    # Test searches across a few different checkpoints.
    # Test title in homage to:
    # https://github.com/compound-finance/compound-protocol/blob/9bcff34a5c9c76d51e51bcb0ca1139588362ef96/tests/Governance/CompTest.js#L157
    @sp.add_test(name="getPriorBalance - generally returns the balance at the appropriate checkpoint - odd number of checkpoints")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND a viewer contract.
        viewer = Viewer(
            t = sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat)
        )
        scenario += viewer

        # AND an alice has 100 tokens
        firstCheckpointLevel = sp.nat(0)
        totalSupply = 100
        scenario += token.mint(
            sp.record(
                value = totalSupply,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = firstCheckpointLevel,
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # And alice transfers Bob 10 tokens at a number of checkpoints such that the list is:
        # +-------+---------+
        # | block | balance |
        # +-------+---------+
        # | 2     | 10      |
        # +-------+---------+
        # | 4     | 20      |
        # +-------+---------+
        # | 6     | 30      |
        # +-------+---------+
        # | 8     | 40      |
        # +-------+---------+
        # | 10    | 50      |
        # +-------+---------+
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 2
        )
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 4
        )
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 6
        )                
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 8
        )
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 10
        )        

        # WHEN balances are requested for each checkpoint
        # THEN the correct answer is returned.

        # Sanity check - there are 5 checkpoints for Bob.
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(5))

        # level = 1
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 1
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 1)
        scenario.verify(viewer.data.last.open_some().result == 0)

        # level = 2
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 2
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 2)
        scenario.verify(viewer.data.last.open_some().result == 10)       

        # level = 3
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 3
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 3)
        scenario.verify(viewer.data.last.open_some().result == 10)

        # level = 4
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 4
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 4)
        scenario.verify(viewer.data.last.open_some().result == 20)         

        # level = 5
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 5
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 5)
        scenario.verify(viewer.data.last.open_some().result == 20)     

        # level = 6
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 6
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 6)
        scenario.verify(viewer.data.last.open_some().result == 30)     

        # level = 7
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 7
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 7)
        scenario.verify(viewer.data.last.open_some().result == 30)     

        # level = 8
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 8
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 8)
        scenario.verify(viewer.data.last.open_some().result == 40)     

        # level = 9
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 9
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 9)
        scenario.verify(viewer.data.last.open_some().result == 40)     

        # level = 10
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 10
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 10)
        scenario.verify(viewer.data.last.open_some().result == 50)     

        # level = 11
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 11
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 11)
        scenario.verify(viewer.data.last.open_some().result == 50)             

    # Test searches across a few different checkpoints.
    # Test title in homage to:
    # https://github.com/compound-finance/compound-protocol/blob/9bcff34a5c9c76d51e51bcb0ca1139588362ef96/tests/Governance/CompTest.js#L157
    @sp.add_test(name="getPriorBalance - generally returns the balance at the appropriate checkpoint - even number of checkpoints")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND a viewer contract.
        viewer = Viewer(
            t = sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat)
        )
        scenario += viewer

        # AND an alice has 100 tokens
        firstCheckpointLevel = sp.nat(0)
        totalSupply = 100
        scenario += token.mint(
            sp.record(
                value = totalSupply,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = firstCheckpointLevel,
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # And alice transfers Bob 10 tokens at a number of checkpoints such that the list is:
        # +-------+---------+
        # | block | balance |
        # +-------+---------+
        # | 2     | 10      |
        # +-------+---------+
        # | 4     | 20      |
        # +-------+---------+
        # | 6     | 30      |
        # +-------+---------+
        # | 8     | 40      |
        # +-------+---------+
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 2
        )
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 4
        )
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 6
        )                
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            sender = Addresses.ALICE_ADDRESS,
            level = 8
        )
     
        # WHEN balances are requested for each checkpoint
        # THEN the correct answer is returned.

        # Sanity check - there are 4 checkpoints for Bob.
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(4))

        # level = 1
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 1
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 1)
        scenario.verify(viewer.data.last.open_some().result == 0)

        # level = 2
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 2
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 2)
        scenario.verify(viewer.data.last.open_some().result == 10)       

        # level = 3
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 3
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 3)
        scenario.verify(viewer.data.last.open_some().result == 10)

        # level = 4
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 4
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 4)
        scenario.verify(viewer.data.last.open_some().result == 20)         

        # level = 5
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 5
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 5)
        scenario.verify(viewer.data.last.open_some().result == 20)     

        # level = 6
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 6
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 6)
        scenario.verify(viewer.data.last.open_some().result == 30)     

        # level = 7
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 7
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 7)
        scenario.verify(viewer.data.last.open_some().result == 30)     

        # level = 8
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 8
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 8)
        scenario.verify(viewer.data.last.open_some().result == 40)     

        # level = 9
        level = 12
        scenario += token.getPriorBalance(
            (
                sp.record(
                    address = Addresses.BOB_ADDRESS,
                    level = 9
                ),
                viewer.typed
            )
        ).run(
            level = level,
        )      
        scenario.verify(viewer.data.last.open_some().address == Addresses.BOB_ADDRESS)
        scenario.verify(viewer.data.last.open_some().level == 9)
        scenario.verify(viewer.data.last.open_some().result == 40)             

    ################################################################
    # transfer
    #
    # Core transfer functionality tests are deferred to the token contract
    # tests by SmartPy. 
    #
    # These tests specifically test the checkpoint functionality, and are largely
    # based off of Compound's tests:
    # https://github.com/compound-finance/compound-protocol/blob/master/tests/Governance/CompTest.js
    ################################################################

    @sp.add_test(name="transfer - counts checkpoints correctly on transfers from owners")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND an alice has 100 tokens
        scenario += token.mint(
            sp.record(
                value = 100,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = sp.nat(0),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # WHEN a series of transfers are made
        # THEN token checkpoints are incremented properly

        # Alice transfers the initial tokens to Bob.
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            level = sp.nat(1),
            sender = Addresses.ALICE_ADDRESS
        )
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(2))
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(1))
        scenario.verify(token.data.numCheckpoints.get(Addresses.CHARLIE_ADDRESS, sp.nat(0)) == sp.nat(0))

        # Alice transfers tokens to Charlie
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.CHARLIE_ADDRESS, 
            value = 10
        ).run(
            level = sp.nat(2),
            sender = Addresses.ALICE_ADDRESS
        )
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(3))
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(1))
        scenario.verify(token.data.numCheckpoints.get(Addresses.CHARLIE_ADDRESS, sp.nat(0)) == sp.nat(1))

        # Bob transfers tokens to Charlie
        scenario += token.transfer(
            from_ = Addresses.BOB_ADDRESS, 
            to_ = Addresses.CHARLIE_ADDRESS, 
            value = 5
        ).run(
            level = sp.nat(3),
            sender = Addresses.BOB_ADDRESS
        )
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(3))
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(2))
        scenario.verify(token.data.numCheckpoints.get(Addresses.CHARLIE_ADDRESS, sp.nat(0)) == sp.nat(2))

        # AND history is recorded correctly for Alice.
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].fromBlock == 0)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].balance == 100)

        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][1].fromBlock == 1)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][1].balance == 90)

        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][2].fromBlock == 2)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][2].balance == 80)

        # AND history is recorded correctly for Bob.
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][0].fromBlock == 1)
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][0].balance == 10)

        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][1].fromBlock == 3)
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][1].balance == 5)

        # AND history is recorded correctly for Charlie.
        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][0].fromBlock == 2)
        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][0].balance == 10)

        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][1].fromBlock == 3)
        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][1].balance == 15)

    @sp.add_test(name="transfer - counts checkpoints correctly on transfers via approvals")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND an alice has 100 tokens
        scenario += token.mint(
            sp.record(
                value = 100,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = sp.nat(0),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # AND Alice has approved Charlie to transfer 100 tokens
        scenario += token.approve(
            spender = Addresses.CHARLIE_ADDRESS,
            value = 100
        ).run(
            sender = Addresses.ALICE_ADDRESS
        )

        # AND Bob has approved Charlie to transfer 100 tokens
        scenario += token.approve(
            spender = Addresses.CHARLIE_ADDRESS,
            value = 100
        ).run(
            sender = Addresses.BOB_ADDRESS
        )

        # WHEN a series of transfers are made via approvals
        # THEN token checkpoints are incremented properly

        # Charlie transfers tokens from Alice to Bob.
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = 10
        ).run(
            level = sp.nat(1),
            sender = Addresses.ALICE_ADDRESS
        )
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(2))
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(1))
        scenario.verify(token.data.numCheckpoints.get(Addresses.CHARLIE_ADDRESS, sp.nat(0)) == sp.nat(0))

        # Charlie transfers tokens from Alice to Charlie.
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.CHARLIE_ADDRESS, 
            value = 10
        ).run(
            level = sp.nat(2),
            sender = Addresses.ALICE_ADDRESS
        )
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(3))
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(1))
        scenario.verify(token.data.numCheckpoints.get(Addresses.CHARLIE_ADDRESS, sp.nat(0)) == sp.nat(1))

        # Charlie transfers tokens from Bob to Charlie.
        scenario += token.transfer(
            from_ = Addresses.BOB_ADDRESS, 
            to_ = Addresses.CHARLIE_ADDRESS, 
            value = 5
        ).run(
            level = sp.nat(3),
            sender = Addresses.BOB_ADDRESS
        )
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(3))
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(2))
        scenario.verify(token.data.numCheckpoints.get(Addresses.CHARLIE_ADDRESS, sp.nat(0)) == sp.nat(2))

        # AND history is recorded correctly for Alice.
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].fromBlock == 0)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].balance == 100)

        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][1].fromBlock == 1)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][1].balance == 90)

        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][2].fromBlock == 2)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][2].balance == 80)

        # AND history is recorded correctly for Bob.
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][0].fromBlock == 1)
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][0].balance == 10)

        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][1].fromBlock == 3)
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][1].balance == 5)

        # AND history is recorded correctly for Charlie.
        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][0].fromBlock == 2)
        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][0].balance == 10)

        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][1].fromBlock == 3)
        scenario.verify(token.data.checkpoints[Addresses.CHARLIE_ADDRESS][1].balance == 15)

    @sp.add_test(name="transfer - does not write two checkpoints for one block")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND an alice has 100 tokens
        totalTokens = 100
        scenario += token.mint(
            sp.record(
                value = totalTokens,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = sp.nat(0),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # WHEN two transfers to Bob are made in the same block.
        transferValue = sp.nat(10)
        level = sp.nat(1)
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = transferValue
        ).run(
            level = level,
            sender = Addresses.ALICE_ADDRESS
        )

        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.BOB_ADDRESS, 
            value = transferValue
        ).run(
            level = level,
            sender = Addresses.ALICE_ADDRESS
        )

        # THEN Alice only records the transfer for the block once.
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(2))
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].fromBlock == 0)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].balance == totalTokens)

        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][1].fromBlock == level)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][1].balance == sp.as_nat(totalTokens - (transferValue * 2)))

        # AND Bob only records one checkpoint        
        scenario.verify(token.data.numCheckpoints.get(Addresses.BOB_ADDRESS, sp.nat(0)) == sp.nat(1))
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][0].fromBlock == level)
        scenario.verify(token.data.checkpoints[Addresses.BOB_ADDRESS][0].balance == (transferValue * 2))

    @sp.add_test(name="transfer - does not write a checkpoint when the sender and receiver are the same")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND an alice has 100 tokens
        totalTokens = 100
        scenario += token.mint(
            sp.record(
                value = totalTokens,
                address = Addresses.ALICE_ADDRESS
            )
        ).run(
            level = sp.nat(0),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # WHEN alice transfers tokens to herself.        
        transferValue = sp.nat(10)
        level = sp.nat(1)
        scenario += token.transfer(
            from_ = Addresses.ALICE_ADDRESS, 
            to_ = Addresses.ALICE_ADDRESS, 
            value = transferValue
        ).run(
            level = level,
            sender = Addresses.ALICE_ADDRESS
        )

        # THEN Alice still has the same amount of tokens
        scenario.verify(token.data.balances[Addresses.ALICE_ADDRESS].balance == totalTokens)

        # AND Alice has one checkpoint
        scenario.verify(token.data.numCheckpoints.get(Addresses.ALICE_ADDRESS, sp.nat(0)) == sp.nat(1))

        # THEN Alice's checkpoint is the initial mint.
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].fromBlock == 0)
        scenario.verify(token.data.checkpoints[Addresses.ALICE_ADDRESS][0].balance == totalTokens)

    ################################################################
    # disableMinting
    ################################################################

    @sp.add_test(name="disableMinting - disables minting")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN minting is diabled
        scenario += token.disableMinting(sp.unit).run(
            sender = Addresses.TOKEN_ADMIN_ADDRESS
        )

        # THEN the state is updated.
        scenario.verify(token.data.mintingDisabled == True)

        # AND future calls to mint fail.
        scenario += token.mint(
            sp.record(
                value = sp.nat(100),
                address = Addresses.TOKEN_RECIPIENT
            )
        ).run(
            level = sp.nat(1),
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
            valid = False
        )

    @sp.add_test(name="disableMinting - fails when not called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN minting is diabled by someone other than the admin
        # THEN the call fails.
        notAdmin = Addresses.NULL_ADDRESS
        scenario += token.disableMinting(sp.unit).run(
            sender = notAdmin,
            valid = False
        )

    ################################################################
    # mint
    ################################################################

    @sp.add_test(name="mint - fails when not called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN mint is called by someone other than the admin
        # THEN it fails.
        value = sp.nat(100)
        level = sp.nat(42)
        notAdmin = Addresses.NULL_ADDRESS
        scenario += token.mint(
            sp.record(
                value = value,
                address = Addresses.TOKEN_RECIPIENT
            )
        ).run(
            level = level,
            sender = notAdmin,
            valid = False
        )

    @sp.add_test(name="mint - fails when minting is locked")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # AND the token contract has minting disabled.
        scenario += token.disableMinting(sp.unit).run(
            sender = Addresses.TOKEN_ADMIN_ADDRESS
        )

        # WHEN mint is called
        # THEN it fails.
        value = sp.nat(100)
        level = sp.nat(42)
        scenario += token.mint(
            sp.record(
                value = value,
                address = Addresses.TOKEN_RECIPIENT
            )
        ).run(
            level = level,
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
            valid = False
        )

    @sp.add_test(name="mint - succeeds when called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN mint is called by the admin contract
        value = sp.nat(100)
        level = sp.nat(42)
        scenario += token.mint(
            sp.record(
                value = value,
                address = Addresses.TOKEN_RECIPIENT
            )
        ).run(
            level = level,
            sender = Addresses.TOKEN_ADMIN_ADDRESS
        )

        # THEN the recipient received the tokens.
        scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == value)

        # AND a single checkpoint was written.
        scenario.verify(token.data.numCheckpoints[Addresses.TOKEN_RECIPIENT] == sp.nat(1))
        scenario.verify(token.data.checkpoints[Addresses.TOKEN_RECIPIENT][0].fromBlock == level)
        scenario.verify(token.data.checkpoints[Addresses.TOKEN_RECIPIENT][0].balance == value)

    @sp.add_test(name="mint - writes checkpoints correctly for multiple mints")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN mint is called by the admin contract twice
        value1 = sp.nat(100)
        level1 = sp.nat(1)
        scenario += token.mint(
            sp.record(
                value = value1,
                address = Addresses.TOKEN_RECIPIENT
            )
        ).run(
            level = level1,
            sender = Addresses.TOKEN_ADMIN_ADDRESS
        )

        value2 = sp.nat(10)
        level2 = sp.nat(2)
        scenario += token.mint(
            sp.record(
                value = value2,
                address = Addresses.TOKEN_RECIPIENT
            )
        ).run(
            level = level2,
            sender = Addresses.TOKEN_ADMIN_ADDRESS
        )

        # THEN the recipient received the tokens.
        scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == (value1 + value2))

        # AND there are two checkpoints written.
        scenario.verify(token.data.numCheckpoints[Addresses.TOKEN_RECIPIENT] == sp.nat(2))

        # AND the first checkpoint was written correctly.
        scenario.verify(token.data.checkpoints[Addresses.TOKEN_RECIPIENT][0].fromBlock == level1)
        scenario.verify(token.data.checkpoints[Addresses.TOKEN_RECIPIENT][0].balance == value1)

        # AND the second checkpoint was written correctly.
        scenario.verify(token.data.checkpoints[Addresses.TOKEN_RECIPIENT][1].fromBlock == level2)
        scenario.verify(token.data.checkpoints[Addresses.TOKEN_RECIPIENT][1].balance == (value1 + value2))

    ################################################################
    # updateContractMetadata
    ################################################################

    @sp.add_test(name="updateContractMetadata - succeeds when called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN the updateContractMetadata is called with a new locator
        locatorKey = ""
        newLocator = sp.bytes('0x1234567890')
        scenario += token.updateContractMetadata((locatorKey, newLocator)).run(
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # THEN the contract is updated.
        scenario.verify(token.data.metadata[locatorKey] == newLocator)

    @sp.add_test(name="updateContractMetadata - fails when not called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN the updateContractMetadata is called by someone who isn't the admin
        # THEN the call fails
        locatorKey = ""
        newLocator = sp.bytes('0x1234567890')
        scenario += token.updateContractMetadata((locatorKey, newLocator)).run(
            sender = Addresses.NULL_ADDRESS,
            valid = False
        )            

    ################################################################
    # updateTokenMetadata
    ################################################################

    @sp.add_test(name="updateTokenMetadata - succeeds when called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN the updateTokenMetadata is called with a new data set.
        newKey = "new"
        newValue = sp.bytes('0x123456')
        newMap = sp.map(
            l = {
                newKey: newValue
            },
            tkey = sp.TString,
            tvalue = sp.TBytes
        )
        newData = sp.record(
          token_id = sp.nat(0), 
          token_info = newMap
        )

        scenario += token.updateTokenMetadata(newData).run(
            sender = Addresses.TOKEN_ADMIN_ADDRESS,
        )

        # THEN the contract is updated.
        tokenMetadata = token.data.token_metadata[0]
        tokenId = tokenMetadata.token_id
        tokenMetadataMap = tokenMetadata.token_info
                
        scenario.verify(tokenId == sp.nat(0))
        scenario.verify(tokenMetadataMap[newKey] == newValue)

    @sp.add_test(name="updateTokenMetadata - fails when not called by admin")
    def test():
        # GIVEN a Token contract
        scenario = sp.test_scenario()

        token = FA12(
            admin = Addresses.TOKEN_ADMIN_ADDRESS,
        )
        scenario += token

        # WHEN the updateTokenMetadata is called by someone who isn't the admin THEN the call fails
        newMap = sp.map(
            l = {
                "new": sp.bytes('0x123456')
            },
            tkey = sp.TString,
            tvalue = sp.TBytes
        )
        newData = sp.record(
          token_id = sp.nat(0), 
          token_info = newMap
        )
        scenario += token.updateTokenMetadata(newData).run(
            sender = Addresses.NULL_ADDRESS,
            valid = False
        )            

    ################################################################
    # Tests from the original SmartPy template.
    ################################################################

    if "templates" not in __name__:
        @sp.add_test(name = "core token tests")
        def test():

            scenario = sp.test_scenario()
            scenario.h1("FA1.2 template - Fungible assets")

            scenario.table_of_contents()

            # sp.test_account generates ED25519 key-pairs deterministically:
            admin = sp.test_account("Administrator")
            alice = sp.test_account("Alice")
            bob   = sp.test_account("Robert")

            # Let's display the accounts:
            scenario.h1("Accounts")
            scenario.show([admin, alice, bob])

            scenario.h1("Contract")
            c1 = FA12(admin.address)

            scenario.h1("Entry points")
            scenario += c1
            scenario.h2("Admin mints a few coins")
            scenario += c1.mint(address = alice.address, value = 12).run(sender = admin)
            scenario += c1.mint(address = alice.address, value = 3).run(sender = admin)
            scenario += c1.mint(address = alice.address, value = 3).run(sender = admin)
            scenario.h2("Alice transfers to Bob")
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 4).run(sender = alice)
            scenario.verify(c1.data.balances[alice.address].balance == 14)        
            scenario.h2("Bob tries to transfer from Alice but he doesn't have her approval")
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 4).run(sender = bob, valid = False)
            scenario.h2("Alice approves Bob and Bob transfers")
            scenario += c1.approve(spender = bob.address, value = 5).run(sender = alice)
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 4).run(sender = bob)
            scenario.h2("Bob tries to over-transfer from Alice")
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 4).run(sender = bob, valid = False)

            # CHANGED: Remove tests for burning.

            scenario.h2("Admin pauses the contract and Alice cannot transfer anymore")
            scenario += c1.setPause(True).run(sender = admin)
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 4).run(sender = alice, valid = False)
            scenario.verify(c1.data.balances[alice.address].balance == 10)
            scenario.h2("Admin transfers while on pause")
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 1).run(sender = admin)
            scenario.h2("Admin unpauses the contract and transferts are allowed")
            scenario += c1.setPause(False).run(sender = admin)
            scenario.verify(c1.data.balances[alice.address].balance == 9)
            scenario += c1.transfer(from_ = alice.address, to_ = bob.address, value = 1).run(sender = alice)

            # CHANGED: Add 1 because burning test was removed.
            scenario.verify(c1.data.totalSupply == 18)
            scenario.verify(c1.data.balances[alice.address].balance == 8)
            # CHANGED: Add 1 because burning test was removed.
            scenario.verify(c1.data.balances[bob.address].balance == 10)

            scenario.h1("Views")
            scenario.h2("Balance")
            view_balance = Viewer(sp.TNat)
            scenario += view_balance
            scenario += c1.getBalance((alice.address, view_balance.typed))
            scenario.verify_equal(view_balance.data.last, sp.some(8))

            scenario.h2("Administrator")
            view_administrator = Viewer(sp.TOption(sp.TAddress))
            scenario += view_administrator
            scenario += c1.getAdministrator((sp.unit, view_administrator.typed))
            scenario.verify_equal(view_administrator.data.last, sp.some(sp.some(admin.address)))

            scenario.h2("Total Supply")
            view_totalSupply = Viewer(sp.TNat)
            scenario += view_totalSupply
            scenario += c1.getTotalSupply((sp.unit, view_totalSupply.typed))
            # CHANGED: Add 1 because burning test was removed.
            scenario.verify_equal(view_totalSupply.data.last, sp.some(18))

            scenario.h2("Allowance")
            view_allowance = Viewer(sp.TNat)
            scenario += view_allowance
            scenario += c1.getAllowance((sp.record(owner = alice.address, spender = bob.address), view_allowance.typed))
            scenario.verify_equal(view_allowance.data.last, sp.some(1))
            
    sp.add_compilation_target("token", FA12())
