import {
  initConseil,
  loadContract,
  deployContract,
  sendOperation,
} from './utils'
import { initOracleLib, Utils } from '@tacoinfra/harbinger-lib'
import { TezosNodeReader } from 'conseiljs'
import CONFIG from './config'
import { BigNumber } from 'bignumber.js'

export type DeployParams = {
  // The node address to deploy to.
  nodeAddress: string

  // The amount to deploy to the faucet
  faucetAmount: BigNumber

  // The amount to deploy to the airdrop
  airdropAmount: BigNumber

  // The address to transfer airdropped tokens to.
  airdropAddress: string

  // Vesting contracts to deploy
  vestingContracts: Array<VestingContract>

  // The amount to escrow for proposals.
  escrowAmount: BigNumber

  // The delay of blocks from when a proposal is submitted to when voting starts.'
  voteDelayBlocks: BigNumber

  // How long a vote lasts.
  voteLengthBlocks: BigNumber

  // The minimum percentage of yay votes for escrow to be returned.
  minYayVotesPercentForEscrowReturn: BigNumber

  // The initial quorum.
  quorum: BigNumber

  // The length of the timelock.
  blocksInTimelockForExecution: BigNumber

  // The minimum number of blocks before anyone can cancel a timelock.
  blocksInTimelockForCancellation: BigNumber

  // The percentage of yay votes for a super majority.
  percentageForSuperMajority: BigNumber

  // Quorum Caps
  upperQuorumCap: BigNumber
  lowerQuorumCap: BigNumber

  // The maximum drip size from the faucet.
  maxFaucetDripSize: BigNumber

  // The governor address
  governorAddress: string
}

export type VestingContract = {
  // The owner of the contract.
  owner: string

  // The block vesting starts on.
  vestingStartBlock: BigNumber

  // The amount that becomes available each block.
  amountPerBlock: BigNumber

  // The amount of tokens in the contract.
  amount: BigNumber
}

// Load secret key
const privateKeyName = 'MURMURATION_DEPLOY_PRIVATE_KEY'
const privateKey = process.env[privateKeyName]

export const deploy = async (params: DeployParams): Promise<void> => {
  console.log('------------------------------------------------------')
  console.log('> Deploying Murmuration Infrastructure')
  console.log('>> Running Pre Flight Checks...')
  console.log('------------------------------------------------------')

  console.log('>>> [1/6] Loading Deployer Key')
  if (privateKey === undefined) {
    console.log('Fatal: No deployer private key defined.')
    console.log(`Set a ${privateKeyName} environment variable..`)
    return
  }
  console.log('Loaded.')
  console.log('')

  console.log('>>> [2/6] Input params:')
  console.log(`Tezos Node: ${params.nodeAddress}`)
  console.log(`Tokens to Mint: ${CONFIG.TOKENS_TO_MINT.toFixed()}`)
  console.log(`Faucet Amount: ${params.faucetAmount.toFixed()}`)
  console.log(`Airdrop Amount: ${params.airdropAmount.toFixed()}`)
  console.log(`Airdrop Address: ${params.airdropAddress}`)
  console.log(`Escrow Amount: ${params.escrowAmount.toFixed()}`)
  console.log(`Vote Delay Blocks: ${params.voteDelayBlocks.toFixed()}`)
  console.log(
    `Minimum Yay Percentage to Retrun Escrow: ${params.minYayVotesPercentForEscrowReturn.toFixed()}`,
  )
  console.log(`Initial Quorum: ${params.quorum.toFixed()}`)
  console.log(
    `Timelock Blocks: ${params.blocksInTimelockForExecution.toFixed()}`,
  )
  console.log(
    `Blocks Before Timelock Can Be Cancelled: ${params.blocksInTimelockForCancellation.toFixed()}`,
  )
  console.log(
    `Percent for Super Majority: ${params.percentageForSuperMajority.toFixed()}`,
  )
  console.log(
    `Quorum Caps: [${params.lowerQuorumCap.toFixed()}, ${params.upperQuorumCap.toFixed()}]`,
  )
  console.log(`Faucet Max Drip Size: ${params.maxFaucetDripSize.toFixed()}`)
  console.log(``)

  console.log(`Vesting Contracts:`)
  for (let i = 0; i < params.vestingContracts.length; i++) {
    console.log(
      `> ${params.vestingContracts[i].owner}: ${params.vestingContracts[
        i
      ].amount.toFixed()}`,
    )
  }
  console.log('')

  console.log(
    `>>> [3/6] Initializing Conseil with logging level: ${CONFIG.LOG_LEVEL}`,
  )
  initConseil(CONFIG.LOG_LEVEL)
  initOracleLib(CONFIG.LOG_LEVEL)
  console.log('Conseil initialized.')
  console.log('')

  console.log('>>> [4/6] Initializing Deployer')
  const keystore = await Utils.keyStoreFromPrivateKey(privateKey)
  await Utils.revealAccountIfNeeded(
    params.nodeAddress,
    keystore,
    await Utils.signerFromKeyStore(keystore),
  )
  console.log(`Initialized deployer: ${keystore.publicKeyHash}`)
  console.log('')

  console.log('>>> [5/6] Loading contracts...')
  const communityFundContract = loadContract(
    `${__dirname}/../../smart_contracts/community-fund.tz`,
  )
  const tokenContract = loadContract(
    `${__dirname}/../../smart_contracts/token.tz`,
  )
  const daoContract = loadContract(`${__dirname}/../../smart_contracts/dao.tz`)
  const faucetContract = loadContract(
    `${__dirname}/../../smart_contracts/faucet.tz`,
  )
  const vestingVaultContract = loadContract(
    `${__dirname}/../../smart_contracts/vesting-vault.tz`,
  )

  console.log('Contracts loaded.')
  console.log('')

  console.log('>>> [6/6] Getting Account Counter')
  let counter = await TezosNodeReader.getCounterForAccount(
    params.nodeAddress,
    keystore.publicKeyHash,
  )
  console.log(`Got counter: ${counter}`)
  console.log('')

  console.log('------------------------------------------------------')
  console.log('>> Preflight Checks Passed!')
  console.log('>> Deploying Contracts...')
  console.log('------------------------------------------------------')
  console.log('')

  console.log('>>> [1/4] Deploying Token Contract')
  counter++
  const tokenContractStorage = `(Pair (Pair (Pair (Some "${keystore.publicKeyHash}") {}) (Pair {} {Elt "" 0x74657a6f732d73746f726167653a64617461; Elt "data" 0x7b20226e616d65223a20224b4f4c20546f6b656e222c20226465736372697074696f6e223a2022546865204641312e3220476f7665726e616e636520546f6b656e20466f72204b6f6c69627269222c2022617574686f7273223a205b22486f766572204c616273203c68656c6c6f40686f7665722e656e67696e656572696e673e225d2c2022686f6d6570616765223a20202268747470733a2f2f6b6f6c696272692e66696e616e6365222c2022696e7465726661636573223a205b2022545a49502d3030372d323032312d30312d3239225d207d})) (Pair (Pair False {}) (Pair False (Pair {Elt 0 (Pair 0 {Elt "decimals" 0x3138; Elt "icon" 0x2068747470733a2f2f6b6f6c696272692d646174612e73332e616d617a6f6e6177732e636f6d2f6c6f676f2e706e67; Elt "name" 0x4b6f6c6962726920476f7665726e616e636520546f6b656e; Elt "symbol" 0x6b44414f})} 0))))`
  const tokenDeployResult = await deployContract(
    tokenContract,
    tokenContractStorage,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('>>> [2/4] Deploying Community Fund')
  counter++
  const communityFundStorage = `(Pair "${keystore.publicKeyHash}" (Pair {Elt "" 0x74657a6f732d73746f726167653a64617461; Elt "data" 0x7b20226e616d65223a20224b4f4c20546f6b656e20436f6d6d756e6974792046756e64222c20226465736372697074696f6e223a2022476f7665726e616e636520546f6b656e2046756e6420666f72204b6f6c696272692044414f222c2022617574686f7273223a205b22486f766572204c616273203c68656c6c6f40686f7665722e656e67696e656572696e673e225d2c2022686f6d6570616765223a20202268747470733a2f2f6b6f6c696272692e66696e616e636522207d0a} "${tokenDeployResult.contractAddress}"))`
  const communityFundDeployResult = await deployContract(
    communityFundContract,
    communityFundStorage,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('>>> [3/4] Deploying DAO')
  counter++
  const daoStorage = `(Pair (Pair (Pair "${communityFundDeployResult.contractAddress
    }" (Pair ${params.escrowAmount.toFixed()} (Pair ${params.voteDelayBlocks.toFixed()} (Pair ${params.voteLengthBlocks.toFixed()} (Pair ${params.minYayVotesPercentForEscrowReturn.toFixed()} (Pair ${params.blocksInTimelockForExecution.toFixed()} (Pair ${params.blocksInTimelockForCancellation.toFixed()} (Pair ${params.percentageForSuperMajority.toFixed()} (Pair ${params.lowerQuorumCap.toFixed()} ${params.upperQuorumCap.toFixed()}))))))))) (Pair {Elt "" 0x74657a6f732d73746f726167653a64617461; Elt "data" 0x7b20226e616d65223a20224b6f6c6962726920476f7665726e616e63652044414f222c20226465736372697074696f6e223a2022476f7665726e616e63652044414f2076302e302e31222c2022617574686f7273223a205b22486f766572204c616273203c68656c6c6f40686f7665722e656e67696e656572696e673e225d2c2022686f6d6570616765223a20202268747470733a2f2f6b6f6c696272692e66696e616e636522207d0a} (Pair 0 {}))) (Pair (Pair None (Pair ${params.quorum.toFixed()} 0)) (Pair None (Pair "${tokenDeployResult.contractAddress
    }" None))))`
  const daoDeployResult = await deployContract(
    daoContract,
    daoStorage,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('>>> [4/4] Deploying Faucet')
  counter++
  const faucetStorage = `(Pair ${params.maxFaucetDripSize.toFixed()} (Pair {Elt "" 0x74657a6f732d73746f726167653a64617461; Elt "data" 0x7b20226e616d65223a20224b4f4c20546f6b656e20466175636574222c20226465736372697074696f6e223a2022476f7665726e616e636520546f6b656e2046617563657420666f72204b6f6c696272692044414f222c2022617574686f7273223a205b22486f766572204c616273203c68656c6c6f40686f7665722e656e67696e656572696e673e225d2c2022686f6d6570616765223a20202268747470733a2f2f6b6f6c696272692e66696e616e636522207d} "${tokenDeployResult.contractAddress
    }"))`
  const faucetDeployResult = await deployContract(
    faucetContract,
    faucetStorage,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('------------------------------------------------------')
  console.log('>> Deploy Complete')
  console.log('>> Minting...')
  console.log('------------------------------------------------------')
  console.log('')

  console.log('>>> [1/2] Minting Tokens')
  counter++
  const mintParam = `Pair "${keystore.publicKeyHash
    }" ${CONFIG.TOKENS_TO_MINT.toFixed()}`
  await sendOperation(
    tokenDeployResult.contractAddress,
    'mint',
    mintParam,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('>>> [2/2] Locking Minting')
  counter++
  await sendOperation(
    tokenDeployResult.contractAddress,
    'disableMinting',
    'Unit',
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('------------------------------------------------------')
  console.log('>> Minting Complete')
  console.log('>> Wiring')
  console.log('------------------------------------------------------')
  console.log('')

  console.log('>>> [1/2] Setting Governor for Community Fund')
  counter++
  await sendOperation(
    communityFundDeployResult.contractAddress,
    'setGovernorContract',
    `"${keystore.publicKeyHash}"`,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('>>> [2/2] Setting Governor for DAO')
  counter++
  await sendOperation(
    tokenDeployResult.contractAddress,
    'setAdministrator',
    `Some "${params.governorAddress}"`,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('------------------------------------------------------')
  console.log('>> Wiring Complete')
  console.log('>> Deploying Vesting Contracts')
  console.log('------------------------------------------------------')
  console.log('')

  const vestingVaultDeployResults = []
  const steps = params.vestingContracts.length * 2
  let step = 0
  for (let i = 0; i < params.vestingContracts.length; i++) {
    const vestingContract = params.vestingContracts[i]
    counter++
    console.log(
      `>>> [${++step}/${steps}] Deploying Vesting Contract for ${vestingContract.owner
      }`,
    )
    const vestingVaultStorage = `(Pair (Pair ${vestingContract.amountPerBlock.toFixed()} (Pair 0 "${daoDeployResult.contractAddress
      }")) (Pair (Pair "${keystore.publicKeyHash}" "${vestingContract.owner
      }") (Pair ${vestingContract.vestingStartBlock.toFixed()} "${tokenDeployResult.contractAddress
      }")))`
    const vestingVaultDeployResult = await deployContract(
      vestingVaultContract,
      vestingVaultStorage,
      keystore,
      counter,
      params.nodeAddress,
    )
    vestingVaultDeployResults.push(vestingVaultDeployResult)
    console.log('')

    counter++
    console.log(
      `>>> [${++step}/${steps}] Transferring Vesting Contract for ${vestingContract.owner
      }`,
    )
    const transferParam = `Pair "${keystore.publicKeyHash}" (Pair "${vestingVaultDeployResult.contractAddress
      }" ${vestingContract.amount.toFixed()})`
    await sendOperation(
      tokenDeployResult.contractAddress,
      'transfer',
      transferParam,
      keystore,
      counter,
      params.nodeAddress,
    )
    console.log(``)
  }

  console.log('------------------------------------------------------')
  console.log('>> Vesting Contracts Deployed and Configured')
  console.log('>> Distributing Tokens')
  console.log('------------------------------------------------------')
  console.log('')

  const totalInVaults = params.vestingContracts.reduce(
    (accumulated: BigNumber, next: VestingContract) => {
      return accumulated.plus(next.amount)
    },
    new BigNumber(0),
  )
  console.log(`Total In Vesting Vaults: ${totalInVaults.toFixed()}`)
  console.log('')

  console.log(`Moving ${params.faucetAmount.toFixed()} Tokens to Faucet`)
  counter++
  const faucetTransferParam = `Pair "${keystore.publicKeyHash}" (Pair "${faucetDeployResult.contractAddress
    }" ${params.faucetAmount.toFixed()})`
  await sendOperation(
    tokenDeployResult.contractAddress,
    'transfer',
    faucetTransferParam,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log(
    `Moving ${params.airdropAmount.toFixed()} Tokens to ${params.airdropAddress
    }`,
  )
  counter++
  const airdropTransferParam = `Pair "${keystore.publicKeyHash}" (Pair "${params.airdropAddress
    }" ${params.airdropAmount.toFixed()})`
  await sendOperation(
    tokenDeployResult.contractAddress,
    'transfer',
    airdropTransferParam,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  const remainder = CONFIG.TOKENS_TO_MINT.minus(totalInVaults)
    .minus(params.faucetAmount)
    .minus(params.airdropAmount)
  console.log(`Moving remaining ${remainder.toFixed()} to Community Fund`)
  counter++
  const communityFundTransferParam = `Pair "${keystore.publicKeyHash}" (Pair "${communityFundDeployResult.contractAddress
    }" ${remainder.toFixed()})`
  await sendOperation(
    tokenDeployResult.contractAddress,
    'transfer',
    communityFundTransferParam,
    keystore,
    counter,
    params.nodeAddress,
  )
  console.log('')

  console.log('------------------------------------------------------')
  console.log('>> Tokens Distributed')
  console.log('>> Murmuration Deploy Complete')
  console.log('> All Done!')
  console.log('------------------------------------------------------')
  console.log('')

  console.log('---------------- Core Contracts ---------------------')
  console.log(
    `Token Contract:          ${tokenDeployResult.contractAddress} (${tokenDeployResult.operationHash})`,
  )
  console.log(
    `Community Fund Contract: ${communityFundDeployResult.contractAddress} (${communityFundDeployResult.operationHash})`,
  )
  console.log(
    `DAO Contract:            ${daoDeployResult.contractAddress} (${daoDeployResult.operationHash})`,
  )
  console.log(
    `Faucet Contract:         ${faucetDeployResult.contractAddress} (${faucetDeployResult.operationHash})`,
  )

  console.log('')
  console.log('---------------- Vesting Contracts ---------------------')

  for (let i = 0; i < vestingVaultDeployResults.length; i++) {
    console.log(
      `${params.vestingContracts[i].owner}: ${vestingVaultDeployResults[i].contractAddress} (${vestingVaultDeployResults[i].operationHash})`,
    )
  }
}
