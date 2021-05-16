# Vesting Vault Contract

A `Vesting Vault` contract custodies a governance token and vests it over time.

The vault keeps track of:
- A start block for vesting
- An amount that vests per block
- The amount of tokens withdrawn.

At any given time, the amount of tokens available to withdraw from the vault is:

```
tokens available for withdrawal = ((current block level - start block level) * tokens vesting per block) - tokens previously withdrawn)
```

When a user wants to withdraw tokens they must specify the amount of tokens to transfer. As long as the requested tokens is less than the tokens available for withdrawal, the request is processed by the vault. If a withdrawal is allowed by the vault, but transfers more tokens than the vault has possession of, the transfer will fail. An advantage of this system is that vaults need not know the amount of tokens they possess and can remain mostly stateless. 

## Governance

Vesting vaults allow their tokens to participate in governance by proposing or by voting. 

In the case of proposing, tokens are escrowed into the governance contract. These tokens are able to be escrowed regardless of vesting state, however, they do not escape the vesting schedule. If the proposal from the vault succeeds, tokens are sent back to the vault, in which case they are subject to the same vesting schedule. If they fail, the tokens are confiscated in the community fund. 

## ACL Checking

The vesting vault has two roles: an `owner` and a `governor`. 

### Owner

The `owner` is the account which is vesting the tokens and may use them for governance. The `owner` may withdraw vested tokens, withdraw other tokens the vault may come into possession of, withdraw XTZ the vault may come into possession of, and use unvested tokens in the governance process. 

### Governor

The `governor` serves as an administrator the vault. The owner is meant to be the `DAO`.

The governor may change the owner of the vault, in case the owner loses their keys or their keys are compromised. The owner may also change the `DAO` contract the `Vesting Vault` uses for governance functions in case the `DAO` contract is upgraded prior to completed vesting. 


## Storage 

The `Vesting Vault` has the following storage fields:
- `amountPerBlock` (`nat`): The amount of tokens that vest per block
- `startBlock` (`nat`): The block vesting begins on
- `governorAddress` (`address`): The address of the `governor`
- `owner` (`address`): The address of the vault's owner
- `tokenContractAddress` (`address`): The address of the token contract that is vesting
- `daoContractAddrss` (`address`): The address of the `DAO` that this vault can use tokens in

## Entrypoints:

The `Vesting Vault` has the following entrypoints:

- `withdraw`: Withdraw the given number of vested tokens to the `owner`.
- `rescueXTZ`: Move some XTZ tokens stored by the `Vesting Vault`. May only be called by the `owner`.
- `rescueFA12`: Moves some FA1.2 tokens stored by the `Vesting Vault`. May only be called by the `owner`. Fails if the token that is requested to be moved is the token that is vesting. 
- `rescueFA2`: Moves some FA2 tokens stored by the `Community Fund`. May only be called by the `owner`. Fails if the token that is requested to be moved is the token that is vesting.
- `rotateOwner`: Change the owner of the vault. May only be called by the `governor`. 
- `setDaoContractAddress`: Change the address of the DAO. Useful if the `DAO` is upgraded prior to vesting finishing. May only be called by the `governor`. 
- `propose`: Uses tokens owned by the `Vesting Vault` to propose a poll in the `DAO` located at `daoContractAddress`. May only be called by the `owner`.
- `vote`: Uses tokens owned by the `Vesting Vault` to vote in a poll in the `DAO` located at `daoContractAddress`. May only be called by the `owner`.
