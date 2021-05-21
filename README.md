# Murmuration

Murmuration is a generalizable DAO built on Tezos. The DAO is used to govern [Kolibri](https://kolibri.finance), but is suitable to govern a number of projects. The DAO takes a lambda and will execute the code in the lambda if the vote passes.

Murmuration provides a complete set of contracts for governance to work out of the box, including:
- The DAO Contract
- A community fund contract that can escrow governance tokens
- Vesting contracts for users
- A token faucet

Deploy scripts are provided to get users up and running with minimal config.

Learn more about Murmuration in the [documentation](docs/README.md).

## Features

The documentation has the complete list of features, but here are a few cool ones:
- Introspective DAO parameters: The DAO can change parameters on itself
- Flash Loan Resistant FA1.2 Token: The DAO uses historical balances to prevent flash loan attacks
- On Chain History: Vote outcomes are preserved without the need of an external indexer
- Optional Timelock: Programatically delay lambda execution
