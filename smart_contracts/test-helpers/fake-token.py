import smartpy as sp

# A contract which fakes a token contract
class FakeTokenContract(sp.Contract):
  def __init__(self, result = sp.nat(3)):
    self.init(result = result)

  @sp.entry_point
  def default(self):
    pass

  @sp.utils.view(sp.TRecord(result = sp.TNat, address = sp.TAddress, level = sp.TNat))
  def getPriorBalance(self, params):
    sp.set_type(params, sp.TRecord(
      address = sp.TAddress,
      level = sp.TNat,
    ).layout(("address", "level")))

    sp.result(
      sp.record(
        result = self.data.result, 
        address = params.address,
        level = params.level,
      )
    )
