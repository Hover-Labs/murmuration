import smartpy as sp

# A dummy contract which can receive and store data for introspection.
#
# This contract can be used in test as a way to capture the results of contract callbacks.
class DummyContract(sp.Contract):
    def __init__(
        self, 
        natValue = sp.nat(0),
        intValue = sp.int(0),
    ):
        self.init(
            natValue = natValue,
            intValue = intValue,
        )

    # Default entrypoint always accepts transfers.
    @sp.entry_point
    def default(self):
        pass

    # Callback for a nat parameter. Places returned value in `natStorage`.
    @sp.entry_point
    def natCallback(self, newNatValue):
        self.data.natValue = newNatValue

    # Callback for a int parameter. Places returned value in `intStorage`.
    @sp.entry_point
    def intCallback(self, newIntValue):
        self.data.intValue = newIntValue       