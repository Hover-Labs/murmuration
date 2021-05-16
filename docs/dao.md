# DAO Contract

The `DAO` contract compromises the majority of the governance system. 

The `DAO` allows users to submit **proposal**s, turning them into **poll**s. Other token holders may vote on polls. If a poll is successful, the proposal is transformed into a **timelock item**. After a **timelock period** the proposal author may execute the proposal, removing it from the timelock, or after a **cancellation period** any user may cancel the proposal, removing it from the timelock without running code. 

## Proposals

A proposal is a set of operations that the `DAO` will execute and metadata about those operations. Specifically, a proposal is comprised of:
- `proposalLambda` (`lambda unit list(operation)`): A lambda that takes a `unit` parameter and returns `list(operation)`
- `title` (`string`): A human readable title describing the intent of the `proposalLambda`
- `descriptionLink` (`string`): A link to a long form discussion of the effects of the `propsalLambda`. 
- `descriptionHash` (`string`): A precomputed hash of the content at `descriptionLink` to guarantee integrity of the link's content.

## Role

The `DAO` is meant to be the `governor` in other Murmuration contracts and in the [Kolibri](https://kolibri.finance) contracts. In this role, the `DAO` will have control of all priviledged roles in the system, and only operation emitted from the `DAO` (via executing a proposal) may modify the system. This state of affairs ensures distributed consensus. 

## State Machine

When a user votes, an intercontract call occurs to fetch the user's balance at the block when the vote began. To do this, a simple state machine is maintained. 

The state machine reads and writes an optional tuple in storage, called `votingState`. `votingState` contains the following fields:
- `voteValue` (`nat`): An enum representing "yay", "nay" or "abstain"
- `address` (`address`): The address which is voting
- `level` (`nat`): The block level the poll started at. 

From the `IDLE` state, the `DAO` can only transition to the `WAITING_FOR_BALANCE` state. The `vote` entrypoint can only be invoked in the `IDLE` state. Ivoking the entrypoint ransitions the `DAO` to the `WAITING_FOR_BALANCE` state. In the `IDLE` state, `votingState` is always `none`.

From the `WAITING_FOR_BALANCE` state, the `DAO` can only transition to the `IDLE` state. The `voteCallback` entrypoint can only be invoked inthe `WAITING_FOR_BALANCE` state. Invoking the entrypoint transitions the `DAO` to the `IDLE` state. In the `WAITING_FOR_BALANCE` state, `votingState` is always `some`.

## Voting Procedure
### Poll Outcomes 

A number of parameters affect the outcome of a poll. Specifically the following numbers are considered:
- Quorum: For a proposal to succeed, the total votes cast (yay + nay + abstain) must be greater than quorum
- Yay Votes for Super Majority: A percentage indicating a super majority. Abstain votes are excluded, such that `yay votes / (nay votes + yay votes)` indicates the percentage
- Minimum Yay Votes for Escrow Return: A percentage of yay votes needed to return the escrow to the proposal author. Abstain votes are excluded,  such that `yay votes / (nay votes + yay votes)` indicates the percentage 

When a poll ends, two independent decisions are made:
- If the poll achieved quorum and a super majority, the proposal is advanced to the timelock. Otherwise, the proposal is removed.
- If the poll achieved the minimum percentage of yay votes for the escrowed tokens are returned to the user. Otherwise they are sent to the community fund. 

### Quorum Adjustments

The quorum for a poll is a weighted moving average of the past quorum and current vote participation, subject to caps. The quorum has both an upper and lower cap, which may not be exceeded. 

At the conclusion of a poll:
- A new quorum is calculated as a weighted average: `new quorum = (.8 * quorum) * (.2 * current participation)`
- If `new quorum > upper quorum cap` then `new quorum = upper quorum cap`
- If `new quorum < lower quorum cap` then `new quorum = lower quorum cap`

## Governance Parameters
### Parameters

The `DAO` parameterizes key components of governance which may be adjusted. Governable governance paramaters are:

- **Escrow Amount**: The amount of tokens escrowed when a user makes a proposal. 
- **Vote Delay Blocks**: The number of blocks to delay between when a proposal is submitted and when voting starts.
- **Vote Length Blocks**: The number of blocks a vote lasts for
- **Minimum Yay Votes for Escrow Return**: The minimum percent of yay votes (vs Nay votes) for the escrow to be returned.
- **Blocks in Timelock for Execution**: The number of blocks a proposal must be in the timelock before it can be executed.
- **Blocks in Timelock for Cancellation**: The number of blocks a proposal must be in the timelock before it can be cancelled.
- **Percentage for Super Majority**: The percentage of a vote that must be yay for a super majority to be achieved. 
- **Quorum Caps**: The upper and lower bounds on quorum. 

### Adjustments

The `setParameters` entrypoint sets a new set of governance parameters. It may only be called by the `DAO`.  This allows users to queue governance polls which emit operations to call `setParameters` and adjust the parameters of governance itself.

## ACL Checking

### `setParameters`

`setParameters` may only be called by the `DAO`. This ensures all governance parameter changes are passed via a vote. 

###  `voteCallback`

`voteCallback` is an entrypoint that is called as part of the voting flow. `voteCallback` may only be called by the `Token` contract, and is subject to the state machine being in the correct state. 

### `executeTimelock`

`executeTimelock` may only be called by the author of the proposal. This is to ensure that the author still agrees that proposal should be executed after the timelock period. 

## Storage

The `DAO` stores the following:
- `tokenContractAddress` (`address`): The address of the `Token` contract which bestows voting rights. 
- `communityFundAddress` (`address`): The address of the `Community Fund`, which recieves escrows which fail to achieve the conditions for return. 
- `governanceParameters` (`tuple`): A tuple of fields which describe the specific parameters of the `DAO`. These parameters are described above. 
- `quorum` (`nat`): The current number of votes required to achieve quorum.
- `poll` (`optional(tuple)`): The current poll and its state if a poll is underway. Otherwise `none`.
- `timelockItem` (`optional(tuple)`): The current item in the timelock if an item is in the timelock. Otherwise `none`.
- `nextProposalId` (`nat`): The next unused ID for a proposal. Proposal IDs are monotonically increasing and unique identifiers that are automatically assigned to proposals.
- `outcomes` (`big_map<nat, tuple>`): A map of proposal IDs to their outcomes. 
- `state` (`nat`): The state of the state machine
- `votingState` (`optional(tuple)`): The saved state of a vote if the state machine's state is `WAITING_FOR_BALANCE`. Otherwise, `none`. 
- `metadata` (`map<string, bytes>`): TZIP-16 compliant metadata for the contract. 

## Entrypoints

The `DAO` has the following entrypoints:
- `propose`: Propose a new proposal, escrowing tokens. The `DAO` must have an approval for the amount of tokens to escrow. 
- `endVoting`: Evaluate the outcome of a poll, if voting has ended. Adjusts quorum, decides where escrow is sent, and optionally advances the proposal to a timelock. 
- `vote`: Vote for a proposal from the sender's address. 
- `voteCallback`: A private callback that returns a voter's token balance.
- `executeTimelock`: Executes a proposal in the timelock, if the timelock period has passed. Fails if the sender is not the proposal's author, or if the timelock period is not elapsed.
- `cancelTimelock`: Removes an item from the timelock, if the cancellation period has passed. Fails if the cancellation period is not elapsed. 
- `setParameters`: Sets new values for governance parameters. May only be called by the `DAO`. 
