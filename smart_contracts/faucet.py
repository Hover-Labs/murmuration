import smartpy as sp

################################################################
################################################################
# Contract
################################################################
################################################################

Addresses = sp.import_script_from_url("file:test-helpers/addresses.py")

# A faucet contract for KOL Governance Tokens
class Faucet(sp.Contract):
    def __init__(
      self, 
      tokenContractAddress = Addresses.TOKEN_CONTRACT_ADDRESS,
      maxTokensPerDrip = 10_000_000_000_000_000_000  
    ):
        # { "name": "KOL Token Faucet", "description": "Governance Token Faucet for Kolibri DAO", "authors": ["Hover Labs <hello@hover.engineering>"], "homepage":  "https://kolibri.finance" }
        metadata_data = sp.bytes('0x7b20226e616d65223a20224b4f4c20546f6b656e20466175636574222c20226465736372697074696f6e223a2022476f7665726e616e636520546f6b656e2046617563657420666f72204b6f6c696272692044414f222c2022617574686f7273223a205b22486f766572204c616273203c68656c6c6f40686f7665722e656e67696e656572696e673e225d2c2022686f6d6570616765223a20202268747470733a2f2f6b6f6c696272692e66696e616e636522207d')

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
          # The maximum value that can be requested in a single drip.
          maxTokensPerDrip = maxTokensPerDrip,
          # Contract metadata.
          metadata = metadata,
        )

    @sp.entry_point
    def default(self, unit):
      sp.set_type(unit, sp.TUnit)
      pass

    # Request a number of tokens from the faucet.    
    @sp.entry_point	
    def drip(self, params):
      sp.set_type(params, sp.TRecord(numberOfTokens = sp.TNat).layout("numberOfTokens"))

      # Verify the requester is not asking for too many tokens.
      sp.verify(params.numberOfTokens <= self.data.maxTokensPerDrip, "TOO_MANY_TOKENS")

      # Request tokens transferred to recipient.
      handle = sp.contract(
        sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
        self.data.tokenContractAddress,
        "transfer"
      ).open_some()
      arg = sp.record(from_ = sp.self_address, to_ = sp.sender, value = params.numberOfTokens)
      sp.transfer(arg, sp.mutez(0), handle)

################################################################
################################################################
# Tests
################################################################
################################################################

# Only run tests if this file is main.
if __name__ == "__main__":

  Token = sp.import_script_from_url("file:token.py")

  ################################################################
  # drip
  ################################################################

  @sp.add_test(name="Drip - succeeds when called with max amount")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a faucet contract.
    maxTokensPerDrip = sp.nat(10)
    faucet = Faucet(
      tokenContractAddress = token.address,
      maxTokensPerDrip = maxTokensPerDrip
    )
    scenario += faucet

    # AND the faucet is funded.
    scenario += token.mint(
      sp.record(
        address = faucet.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN drip is called.
    scenario += faucet.drip(
      sp.record(
        numberOfTokens = maxTokensPerDrip
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT
    )

    # THEN the recipient received the tokens.
    scenario.verify(token.data.balances[Addresses.TOKEN_RECIPIENT].balance == maxTokensPerDrip)

  @sp.add_test(name="Drip - fails when called with more than max amount")
  def test():
    scenario = sp.test_scenario()

    # GIVEN a token contract
    token = Token.FA12(
      admin = Addresses.TOKEN_ADMIN_ADDRESS,
    )
    scenario += token
    
    # AND a faucet contract.
    maxTokensPerDrip = sp.nat(10)
    faucet = Faucet(
      tokenContractAddress = token.address,
      maxTokensPerDrip = maxTokensPerDrip
    )
    scenario += faucet

    # AND the faucet is funded.
    scenario += token.mint(
      sp.record(
        address = faucet.address,
        value = sp.nat(100)
      )
    ).run(
      sender = Addresses.TOKEN_ADMIN_ADDRESS
    )

    # WHEN drip is called with more tokens than allowed
    # THEN the call fails.
    tooManyTokens = maxTokensPerDrip * 2
    scenario += faucet.drip(
      sp.record(
        numberOfTokens = tooManyTokens
      )
    ).run(
      sender = Addresses.TOKEN_RECIPIENT,
      valid = False
    )

  sp.add_compilation_target("faucet", Faucet())
