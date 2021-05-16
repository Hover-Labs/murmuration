import smartpy as sp

# A contract which stores a value that may only be set by the admin.
class StoreValueContract(sp.Contract):
  def __init__(self, value, admin):
    self.init(storedValue = value, admin=admin)

  @sp.entry_point
  def default(self, params):
    pass

  @sp.entry_point
  def setAdmin(self, newAdmin):
    sp.set_type(newAdmin, sp.TAddress)
    self.data.admin = newAdmin

  @sp.entry_point
  def replace(self, newValue):
    sp.verify(sp.sender == self.data.admin, "NOT_ADMIN")       
    self.data.storedValue = newValue