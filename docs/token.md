# Token Contract

The `Token` contract provides an augmented version of an FA1.2. 

There are two sets of augmentations made. 

The first augmentation allows historical balances may be queried. The base implementation of the FA1.2 standard is provided by SmartPy. The augmentation logic is heavily influenced by [Compound's COMP Governance token](https://github.com/compound-finance/compound-protocol/blob/master/contracts/Governance/Comp.sol).

The second augmentation allows minting of tokens to be verifiably locked (and the `burn` entrypoint is removed). This ensures that the tokens issued have a maximum supply that can never be adjusted. 

## Checkpoints

A checkpoint is a tuple representing a change in balance for an account:
- **fromBlock**: The block the balance was changed on
- **balance**: The balance of the account. 

Checkpoints are written whenever a balance changes via transferring or minting / burning.

Two additional data structures are used to track checkpoints:
- `checkpoints`: (`map<address, map<nat, checkpoint>>`): A map of addresses to lists of checkpoints. Since Michelson cannot perform random list accesses, a nested map is used. 
- `numCheckpoints` (`map<address, nat>`): A map of addresses to the number of checkpoints.

## Complexity

### Writing Checkpoints

When a checkpoint is created, two updates occur:
1. A new checkpoint is written into `checkpoints[<ADDRESS>][numCheckpoints<ADDRESS>]`.
2. The value in `numCheckpoints[<ADDRESS>]` is incremented.

This logic runs in constant time. 

### Reading Checkpoints

When a balance requested at a block, `n`, we must search all checkpoints to find what the balance was at that block. This is done via a binary search, which runs in `ln(number of checkpoints)` time, and thus may be arbitrarily large. In cases of accounts which have a large number of checkpoints, this could eventually cause gas issues. 

If an account ever gained a sufficiently large number of checkpoints such that gas is exhausted when a checkpoint is attempted to be read, the user wuld need to move the entirety of tokens to a new address (which starts with zero checkpoints). Since the transfer operation will only write checkpoints (which runs in `O(1)` time) user will always be able to reset their checkpoints. 

Given the optimizations occuring in Michelson's execution engine, and the benefits which checkpoints provide for flash loan resistance, we choose to ignore the theoretical limits on the number of checkpoitns. 

### ACL Checking

The token contract has an `administrator` which is of type `optional(address)` and which may execute priviledged functions. The administrator may:
1. Call `mint` to create new tokens.
2. Call `disableMinting` to permanently disable future minting. 
3. Call `updateContractMetadata` or `updateTokenMetadata` to update TZIP-16 metadata to comply with emerging standards. 
4. Call `transfer` to move tokens between any accounts. 
5. Call `setPause` to pause token transfers.
6. Call `setAdministrator` to change the administrator to another account, or set to `none` to permanently lock admin functions. 

On deploy, it is intended that the `administrator` will create an atomic transaction which:
1. Calls `mint` to create the maximum supply of tokens
2. Calls `disableMinting` to lock the supply of tokens

The administrator is intended to be the `DAO`. The `DAO` may vote at any time to call `setAdministrator(none)` to permanently lock the role when such a vote is capable of passing governance. 

## Storage

The `Token` contract stores the standard FA1.2 fields in the SmartPy FA1.2 template, plus these additional fields:
- `checkpoints` (`big_map<address, map<nat, checkpoint>>`): A map of addresses to a numbered list of checkpoints. 
- `numCheckpoints` (`big_map<address, nat>`): A map of addresses to the number of checkpoints in the list. 
- `mintingDisabled` (`boolean`): If true, the token will not allow mint operations.
- `administrator` (`optional<address>`): The address that is the administrator, or `none` if there is no administrator. 
- `metadata` (`map<string, bytes>`): TZIP-16 compliant metadata
- `token_metadata` (`map<nat, map<string, bytes>`>): TZIP-7 compliant token metadata

## Entrypoints

The `Token` contract has the standard FA1.2 entrypoints in the SmartPy FA1.2 template. Omissions, modifications and additions are listed below:
- `updateContractMetadata`: Updates the TZIP-16 contract metadata. May only be called by the `administrator`. 
- `updateTokenMetadata`: Updates the TZIP-7 token metadata. May only be called by the `administrator`. 
- `getPriorBalance`: Given a block height, an address, and a callback, this entrypoint will determine the given address' balance at the block height and call the callback with the input parameters and the result. 
- `disableMinting`: Disables minting by setting the `mintingDisabled` field in storage to `True`. 
- `mint`: Mints tokens, unless `mintingDisabled` is set to `True`.
- `setAdministrator`: Takes an `option(address)` rather than `address` as a parameter so that the administrator functions can be locked. 
