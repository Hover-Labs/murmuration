# Community Fund Contract

The `Community Fund` contract provides a way for the governance system to custody governance tokens that are held in the escrow for future distribution. The `Community Fund` also receives escrows from proposals which did not meet the requirements for escrow returns.

The `Community Fund` has a priviledged address, called the `governor`. The `governor` is the only user who can interact with the fund to move tokens. Generally, the `governor` is the DAO. The `governor` address may also assign a new `governor`, which is useful in case the `DAO` is upgraded.

This separation of concerns between custodying of funds (`Community Fund` Contract) and voting on how they are used (`DAO` Contract) provides better encapsulation and separation of concerns. It also makes it easy to upgrade voting logic without needing to move funds.

Lastly, the `Community Fund` is primarily meant as a way to custody governance tokens. However, the fund provides generalized entrypoints for custodying any FA1.2 or FA2 tokens, or for custodying XTZ. This allows maximum extensibility and flexibility in the governance system's ability to custody any funds that make sense. 

### ACL Checking

Entrypoints in the `Community Fund` are only callabel from the `Governor` contract.

## Storage

The `Community Fund` stores the following:
- `tokenContractAddress` (`address`): The address of the governance token contract.
- `governorAddress` (`address`): The address of the governor. 
- `metadata` (`map<string, bytes>`): TZIP-16 compliant metadata describing the contract.

## Entrypoints

The `Community Fund` has the following entrypoints:
- `send`: Send some governance tokens to a destination. May only be called by the `governor`.
- `rescueXTZ`: Move some XTZ tokens stored by the `Community Fund`. May only be called by the `governor`.
- `rescueFA12`: Moves some FA1.2 tokens stored by the `Community Fund`. May only be called by the `governor`. 
- `rescueFA2`: Moves some FA2 tokens stored by the `Community Fund`. May only be called by the `governor`. 
- `setDelegate`: Set the baker for the contract. May only be called by the `governor`.
