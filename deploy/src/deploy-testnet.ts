import { BigNumber } from 'bignumber.js'
import { DeployParams, deploy } from './deploy-murmuration'
import { scaleTokenAmount } from './utils'

const params: DeployParams = {
  nodeAddress: 'https://testnet-tezos.giganode.io',

  vestingContracts: [
    {
      owner: 'tz1YfB2H1NoZVUq4heHqrVX4oVp99yz8gwNq',
      amountPerBlock: new BigNumber('0.08561643835'),
      vestingStartBlock: new BigNumber('210700'),
      amount: scaleTokenAmount(new BigNumber('90000')),
    },
    {
      owner: 'tz1QM9J63wfTrGW7HLotr7Kshy8q8LhdorJe',
      amountPerBlock: new BigNumber('0.08561643835'),
      vestingStartBlock: new BigNumber('210700'),
      amount: scaleTokenAmount(new BigNumber('90000')),
    },
    {
      owner: 'tz1YvwHP7TDbAMWf2sFZ5AzjRPe4GyA7Fc46',
      amountPerBlock: new BigNumber('0.01902587519'),
      vestingStartBlock: new BigNumber('210700'),
      amount: scaleTokenAmount(new BigNumber('20000')),
    },
  ],

  faucetAmount: scaleTokenAmount(new BigNumber('0')),
  maxFaucetDripSize: scaleTokenAmount(new BigNumber('0')),

  airdropAmount: scaleTokenAmount(new BigNumber('150000')),
  airdropAddress: 'tz1hoverof3f2F8NAavUyTjbFBstZXTqnUMS',

  escrowAmount: scaleTokenAmount(new BigNumber('10000')),
  voteDelayBlocks: new BigNumber('1'),
  voteLengthBlocks: new BigNumber('20160'),

  minYayVotesPercentForEscrowReturn: new BigNumber('20'),

  blocksInTimelockForExecution: new BigNumber('8640'),
  blocksInTimelockForCancellation: new BigNumber('14400'),

  percentageForSuperMajority: new BigNumber('65'),

  quorum: scaleTokenAmount(new BigNumber('200000')),
  upperQuorumCap: scaleTokenAmount(new BigNumber('900000')),
  lowerQuorumCap: scaleTokenAmount(new BigNumber('10000')),

  governorAddress: 'tz1hoverof3f2F8NAavUyTjbFBstZXTqnUMS',
}

void deploy(params)
