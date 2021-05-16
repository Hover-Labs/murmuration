# Murmuration

Murmuration is a DAO that allows token holders to vote on a proposal. If a vote passes, then the proposal is moved into a timelock. Murmuration is primarily meant as a governance tool for [Kolibri](https://kolibri.finance) but is generalizable.

A vote passes in Murmuration if it has a super majority and achieves quorum. Voters may choose to vote 'Yay', 'Nay' or 'Abstain' on a proposal. Votes are immutable and may not be changed after submission. 

Votes in Murmuration are carried out with a customized FA1.2 token. The token provides a historical record of users' balances, which provides resistance to manipulation of the DAO via flash loans. This behavior is based off [Compound's COMP token](https://github.com/compound-finance/compound-protocol/blob/master/contracts/Governance/Comp.sol).

Lastly, Murmuration keeps a historic record of all outcomes on chain.

## Contacts

The Murmuration system is designed to be a complete solution for Governance and is composed of several contracts:
- [DAO](dao.md): The DAO which provides governance and voting function
- [Token](token.md): The token which provides voting rights to holders
- [Community Fund](community-fund.md): A fund which is controlled by the DAO and custodies governance tokens not in circulation.
- [Vesting Vault](vesting-vault.md): A contract which escrows tokens and vests them to a user over time. 
- [Faucet](faucet.md): A contract which provides a faucet of governance tokens when deployed on testnet.

## Governance Flow

A proposal goes through several phases in Murmuration:
1. A user submits a **proposal**, which becomes a **poll**
2. A voting period occurs, where voters vote on the poll 
3. If the poll passes, it is moved to the timelock
4. After a timelock period, the proposal may be executed by the user who submitted it. 
5. After a cancellation period, the proposal may be cancelled by any user. 

## Data Types

### Proposals

A **proposal** to the DAO is a set of data that encompasses the following:
- **Title**: A title of the proposal
- **Description Link**: A link to a long form description of the proposal.
- **Description Hash**: A hash of the content at the description link, to prevent manipulation. 
- **Lambda**: A lambda that takes a parameter of type `unit` and returns a `list(operation)` which will be executed if the proposal passes. 

Proposals are submitted to the DAO by holders. 

### Poll

When a proposal is submitted, it becomes a **poll**.

A poll has all the data in proposal, plus some additional fields:
- **ID**: An automatically assigned and monotonically increasing ID number.
- **Voting Start Block**: The first block of voting.
- **Voting End Block**: The last block of voting.
- **Yay Votes**: The number of tokens that have voted 'Yay'
- **Nay Votes**: The number of tokens that have voted 'Nay'
- **Abstain Votes**: The number of tokens that have voted 'Abstain'
- **Total Votes**: The total number of tokens that have voted. 
- **Voters**: A list of voters
- **Author**: The public key hash which submitted the proposal which created the poll. 
- **Escrow Amount**: The amount of tokens escrowed as part of the proposal. 
- **Quorum Cap**: The current quorum caps of the proposal. 

### TimeLock Item

If a poll passes, it becomes a **timelock item**. 

A timelock item has all the fields in the proposal, plus some additional fields:
- **ID**: An automatically assigned and monotonically increasing ID number. This is the same number as the poll. 
- **End Block**: The block the timelock ends on and when the author may execute the proposal.
- **Cancellation Block**: The block the item may be cancelled on by any user. 
- **Author**: The author of the proposal. Only the author can execute the item. 

### Historical Outcome

When a poll is finished, the result is stored as a **historical outcome**. 

A historical outcome contains all the data in a poll, plus one additional field:
- **Outcome**: An enum representing the state of the proposal. 

The outcome enum states are as follows:
- **Failed**: The poll did not pass the vote and was removed. 
- **In Timelock**: The poll passed and is currently in the timelock
- **Executed**: The poll passed, and was executed after the timelock period ended
- **Cancelled** The poll passed, and was cancelled after the cancellation period ended.

## Governance Parameters

A set of Governance parameters are used to customize the behavior of Murmuration. They are:
- **Escrow Amount**: The amount of tokens escrowed when a user makes a proposal. 
- **Vote Delay Blocks**: The number of blocks to delay between when a proposal is submitted and when voting starts.
- **Vote Length Blocks**: The number of blocks a vote lasts for
- **Minimum Yay Votes for Escrow Return**: The minimum percent of yay votes (vs Nay votes) for the escrow to be returned.
- **Blocks in Timelock for Execution**: The number of blocks a proposal must be in the timelock before it can be executed.
- **Blocks in Timelock for Cancellation**: The number of blocks a proposal must be in the timelock before it can be cancelled.
- **Percentage for Super Majority**: The percentage of a vote that must be yay for a super majority to be achieved. 
- **Quorum Caps**: The upper and lower bounds on quorum. 

Importantly, these governance parameters may changed by Governance themselves.

## Design Rational

Murmuration takes an opinionated approach to governance and 

### Spam Prevention

Murmuration only allows a single poll to be underway at a time. As such, users may front run polls as a denial of service attack to prevent real proposals from being put forth. 

To prevent this attack, Murmuration escrows a number of tokens from the user when they make a proposal. If the proposal does not achieve a minimum number of 'Yay' votes, the escrowed tokens are confiscated, otherwise they are returned to the user at the conclusion of a poll. 

This also serves as a strong incentive for users to coordinate their proposals off chain and achieve broad consensus before submitting a proposal, which serves to limit the number of controversial or failing proposals that are actually put up for a vote.

### Execution Safety

Only the submitter of a proposal may ultimately execute the proposal. This is a safety measure as the author of the proposal is likely to understand best the effects of the proposal. If conditions change while the proposal is timelocked, it may be advantageous to ultimately not execute the proposal. By giving the author a priviledged role, we limit the chance of a proposal being executed in a disadvantageous context. 

In the case that the author loses their keys or is unavailable, any user can cancel the timelock after a cancellation period. This discards the propsoal and frees the timelock for a future proposal. 

### Flash Loan Resistance

The token contract snapshots balance whenever it changes. Only one snapshot may occur in each block. When voting, the number of tokens the user can use to vote is determined by the balance the user had on the first block of the vote. 

In practice, this means users must hold tokens for at least one block to receive voting rights. This means that the user will pay interest on any oan they take and provides resistance against flash loans. 