import { BigNumber } from 'bignumber.js'
import { DeployParams, deploy } from './deploy-murmuration'
import { scaleTokenAmount } from './utils'

const params: DeployParams = {
  nodeAddress: 'https://rpctest.tzbeta.net',

  vestingContracts: [
    {
      owner: 'tz1YfB2H1NoZVUq4heHqrVX4oVp99yz8gwNq',
      amountPerBlock: scaleTokenAmount(new BigNumber('2')),
      vestingStartBlock: new BigNumber('170800'),
      amount: scaleTokenAmount(new BigNumber('10000')),
    },
    {
      owner: 'tz1QM9J63wfTrGW7HLotr7Kshy8q8LhdorJe',
      amountPerBlock: scaleTokenAmount(new BigNumber('3')),
      vestingStartBlock: new BigNumber('170900'),
      amount: scaleTokenAmount(new BigNumber('10000')),
    },
    {
      owner: 'tz1YvwHP7TDbAMWf2sFZ5AzjRPe4GyA7Fc46',
      amountPerBlock: scaleTokenAmount(new BigNumber('4')),
      vestingStartBlock: new BigNumber('171000'),
      amount: scaleTokenAmount(new BigNumber('10000')),
    },
  ],

  faucetAmount: scaleTokenAmount(new BigNumber('100000')),
  maxFaucetDripSize: scaleTokenAmount(new BigNumber('100')),

  airdropAmount: scaleTokenAmount(new BigNumber('200000')),
  airdropAddress: 'tz1KoLibimdjUSfhrSpXwx4FhhhCq1JM5Etk',

  escrowAmount: scaleTokenAmount(new BigNumber('100')),
  voteDelayBlocks: new BigNumber('1'),
  voteLengthBlocks: new BigNumber('480'),

  minYayVotesPercentForEscrowReturn: new BigNumber('20'),

  blocksInTimelockForExecution: new BigNumber('120'),
  blocksInTimelockForCancellation: new BigNumber('240'),

  percentageForSuperMajority: new BigNumber('80'),

  quorum: scaleTokenAmount(new BigNumber('2000')),
  upperQuorumCap: scaleTokenAmount(new BigNumber('900000')),
  lowerQuorumCap: scaleTokenAmount(new BigNumber('10000')),

  governorAddress: 'tz1hoverof3f2F8NAavUyTjbFBstZXTqnUMS',
}

void deploy(params)
