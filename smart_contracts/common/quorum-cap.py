import smartpy as sp

# A type representing a quorum cap. 
# Params:
# - lower (nat): The lower bound
# - upper (nat): The upper bound
QUORUM_CAP_TYPE = sp.TRecord(
  lower = sp.TNat, 
  upper = sp.TNat
).layout(("lower", "upper")) 
