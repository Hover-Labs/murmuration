# Faucet Contract

The `Faucet` contract provides a faucet of governance tokens to be used on Testnet. 

## Storage

The `Faucet` stores the following:
- `tokenContractAdddress` (`address`): The address of the token contract. 
- `maxTokensPerDrip` (`nat`): The maximum number of tokens that can be dripped from the faucet in each call. 

## Entrypoints
- `drip`: Send the requested number of tokens to the caller's address. 
