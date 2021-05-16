# Fungible Assets - FA12
# Inspired by https://gitlab.com/tzip/tzip/blob/master/A/FA1.2.md

import smartpy as sp

class FA12_core(sp.Contract):
    def __init__(self, **extra_storage):
        self.init(balances = sp.big_map(tvalue = sp.TRecord(approvals = sp.TMap(sp.TAddress, sp.TNat), balance = sp.TNat)), totalSupply = 0, **extra_storage)

    @sp.entry_point
    def transfer(self, params):
        sp.set_type(params, sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))))
        sp.verify(self.is_administrator(sp.sender) |
            (~self.is_paused() &
                ((params.from_ == sp.sender) |
                 (self.data.balances[params.from_].approvals[sp.sender] >= params.value))))
        self.addAddressIfNecessary(params.to_)
        sp.verify(self.data.balances[params.from_].balance >= params.value)
        self.data.balances[params.from_].balance = sp.as_nat(self.data.balances[params.from_].balance - params.value)
        self.data.balances[params.to_].balance += params.value
        sp.if (params.from_ != sp.sender) & (~self.is_administrator(sp.sender)):
            self.data.balances[params.from_].approvals[sp.sender] = sp.as_nat(self.data.balances[params.from_].approvals[sp.sender] - params.value)

    @sp.entry_point
    def approve(self, params):
        sp.set_type(params, sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")))
        sp.verify(~self.is_paused())
        alreadyApproved = self.data.balances[sp.sender].approvals.get(params.spender, 0)
        sp.verify((alreadyApproved == 0) | (params.value == 0), "UnsafeAllowanceChange")
        self.data.balances[sp.sender].approvals[params.spender] = params.value

    def addAddressIfNecessary(self, address):
        sp.if ~ self.data.balances.contains(address):
            self.data.balances[address] = sp.record(balance = 0, approvals = {})

    @sp.view(sp.TNat)
    def getBalance(self, params):
        sp.result(self.data.balances[params].balance)

    @sp.view(sp.TNat)
    def getAllowance(self, params):
        sp.result(self.data.balances[params.owner].approvals[params.spender])

    @sp.view(sp.TNat)
    def getTotalSupply(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.totalSupply)

    # this is not part of the standard but can be supported through inheritance.
    def is_paused(self):
        return sp.bool(False)

    # this is not part of the standard but can be supported through inheritance.
    def is_administrator(self, sender):
        return sp.bool(False)

class FA12_mint_burn(FA12_core):
    @sp.entry_point
    def mint(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))
        sp.verify(self.is_administrator(sp.sender))
        self.addAddressIfNecessary(params.address)
        self.data.balances[params.address].balance += params.value
        self.data.totalSupply += params.value

    @sp.entry_point
    def burn(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))
        sp.verify(self.is_administrator(sp.sender))
        sp.verify(self.data.balances[params.address].balance >= params.value)
        self.data.balances[params.address].balance = sp.as_nat(self.data.balances[params.address].balance - params.value)
        self.data.totalSupply = sp.as_nat(self.data.totalSupply - params.value)

class FA12_administrator(FA12_core):
    def is_administrator(self, sender):
        return sender == self.data.administrator

    @sp.entry_point
    def setAdministrator(self, params):
        sp.set_type(params, sp.TAddress)
        sp.verify(self.is_administrator(sp.sender))
        self.data.administrator = params

    @sp.view(sp.TAddress)
    def getAdministrator(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.administrator)

class FA12_pause(FA12_core):
    def is_paused(self):
        return self.data.paused

    @sp.entry_point
    def setPause(self, params):
        sp.set_type(params, sp.TBool)
        sp.verify(self.is_administrator(sp.sender))
        self.data.paused = params

class FA12(FA12_mint_burn, FA12_administrator, FA12_pause, FA12_core):
    def __init__(self, admin):
        FA12_core.__init__(self, paused = False, administrator = admin)

class Viewer(sp.Contract):
    def __init__(self, t):
        self.init(last = sp.none)
        self.init_type(sp.TRecord(last = sp.TOption(t)))
    @sp.entry_point
    def target(self, params):
        self.data.last = sp.some(params)


# Only run tests if this file is main.
if __name__ == "__main__":

  if "templates" not in __name__:
      @sp.add_test(name = "FA12")
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
          scenario.h2("Admin burns Bob token")
          scenario += c1.burn(address = bob.address, value = 1).run(sender = admin)
          scenario.verify(c1.data.balances[alice.address].balance == 10)
          scenario.h2("Alice tries to burn Bob token")
          scenario += c1.burn(address = bob.address, value = 1).run(sender = alice, valid = False)
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

          scenario.verify(c1.data.totalSupply == 17)
          scenario.verify(c1.data.balances[alice.address].balance == 8)
          scenario.verify(c1.data.balances[bob.address].balance == 9)

          scenario.h1("Views")
          scenario.h2("Balance")
          view_balance = Viewer(sp.TNat)
          scenario += view_balance
          scenario += c1.getBalance((alice.address, view_balance.typed))
          scenario.verify_equal(view_balance.data.last, sp.some(8))

          scenario.h2("Administrator")
          view_administrator = Viewer(sp.TAddress)
          scenario += view_administrator
          scenario += c1.getAdministrator((sp.unit, view_administrator.typed))
          scenario.verify_equal(view_administrator.data.last, sp.some(admin.address))

          scenario.h2("Total Supply")
          view_totalSupply = Viewer(sp.TNat)
          scenario += view_totalSupply
          scenario += c1.getTotalSupply((sp.unit, view_totalSupply.typed))
          scenario.verify_equal(view_totalSupply.data.last, sp.some(17))

          scenario.h2("Allowance")
          view_allowance = Viewer(sp.TNat)
          scenario += view_allowance
          scenario += c1.getAllowance((sp.record(owner = alice.address, spender = bob.address), view_allowance.typed))
          scenario.verify_equal(view_allowance.data.last, sp.some(1))

      sp.add_compilation_target("FA1_2", FA12(admin = sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr")))
