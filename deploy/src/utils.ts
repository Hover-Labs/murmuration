import fetch from 'node-fetch'
import { getLogger, LogLevelDesc } from 'loglevel'
import {
  KeyStore,
  registerFetch,
  registerLogger,
  TezosNodeWriter,
  TezosParameterFormat,
} from 'conseiljs'
import fs = require('fs')
import {
  Constants,
  OperationFeeEstimator,
  Utils,
} from '@tacoinfra/harbinger-lib'
import { BigNumber } from 'bignumber.js'

/* eslint-disable  @typescript-eslint/no-unsafe-member-access */

// How long to wait after an operation broadcast to move on.
// Blocks on mainnet are 60s, blocks on testnet are 30s. Prefer at least 2 blocks in case of a priority 1 bake.
export const OPERATION_DELAY_SECS = 10

export interface ContractOriginationResult {
  operationHash: string
  contractAddress: string
}

export function loadContract(filename: string): string {
  const contractFile = filename
  const contract = fs.readFileSync(contractFile).toString()
  return contract
}

export function initConseil(conseilLogLevel: LogLevelDesc): void {
  const logger = getLogger('conseiljs')
  logger.setLevel(conseilLogLevel, false)

  registerLogger(logger)
  registerFetch(fetch)
}

/**
 * Scales a token amount (ex. 123) to a natural number with the token scale.
 * @param tokenAmount
 */
export function scaleTokenAmount(tokenAmount: BigNumber): BigNumber {
  const tokenScale = 18
  return tokenAmount.times(new BigNumber('10').pow(tokenScale))
}

export async function sendOperation(
  contractAddress: string,
  entrypoint: string,
  parameter: string,
  keystore: KeyStore,
  counter: number,
  nodeAddress: string,
): Promise<string> {
  try {
    console.log(`Using counter: ${counter}`)

    const signer = await Utils.signerFromKeyStore(keystore)

    await Utils.revealAccountIfNeeded(
      nodeAddress,
      keystore,
      await Utils.signerFromKeyStore(keystore),
    )

    const operation = TezosNodeWriter.constructContractInvocationOperation(
      keystore.publicKeyHash,
      counter,
      contractAddress,
      0,
      0,
      Constants.storageLimit,
      Constants.gasLimit,
      entrypoint,
      parameter,
      TezosParameterFormat.Michelson,
    )

    const operationFeeEstimator = new OperationFeeEstimator(nodeAddress)
    const operationWithFees = await operationFeeEstimator.estimateAndApplyFees([
      operation,
    ])

    // Hack: Apply a fee offset since estimation appears wrong on edo.
    // TODO(keefertaylor): Investigate and resolve.
    for (let i = 0; i < operationWithFees.length; i++) {
      const op = operationWithFees[i]
      op.fee = `${parseInt(op.fee) + 1000}` // + .001 XTZ
      operationWithFees[i] = op
    }

    const nodeResult = await TezosNodeWriter.sendOperation(
      nodeAddress,
      operationWithFees,
      signer,
    )

    const operationHash = nodeResult.operationGroupID
      .replace(/"/g, '')
      .replace(/\n/, '')
    console.log(`Invoked in operation hash: ${operationHash}`)

    // Seems like sometimes Node's mempools run a little slow.
    await Utils.sleep(OPERATION_DELAY_SECS)

    return operationHash
  } catch (e) {
    console.log('Caught exception, retrying...')
    console.log(e)
    await Utils.sleep(OPERATION_DELAY_SECS)

    return sendOperation(
      contractAddress,
      entrypoint,
      parameter,
      keystore,
      counter,
      nodeAddress,
    )
  }
}

export async function deployContract(
  contractSource: string,
  storage: string,
  keystore: KeyStore,
  counter: number,
  nodeAddress: string,
  isMicheline = false,
): Promise<ContractOriginationResult> {
  try {
    console.log(`Using storage: ${storage}`)
    console.log(`Using counter: ${counter}`)

    await Utils.revealAccountIfNeeded(
      nodeAddress,
      keystore,
      await Utils.signerFromKeyStore(keystore),
    )

    const signer = await Utils.signerFromKeyStore(keystore)

    const operation = TezosNodeWriter.constructContractOriginationOperation(
      keystore,
      0,
      undefined,
      0,
      Constants.storageLimit,
      Constants.gasLimit,
      contractSource,
      storage,
      isMicheline
        ? TezosParameterFormat.Micheline
        : TezosParameterFormat.Michelson,
      counter,
    )

    const operationFeeEstimator = new OperationFeeEstimator(nodeAddress)
    const operationnWithFees = await operationFeeEstimator.estimateAndApplyFees(
      [operation],
    )

    const nodeResult = await TezosNodeWriter.sendOperation(
      nodeAddress,
      operationnWithFees,
      signer,
    )

    const operationHash = nodeResult.operationGroupID
      .replace(/"/g, '')
      .replace(/\n/, '')
    const contractAddress = Utils.calculateContractAddress(operationHash, 0)

    console.log(`Deployed in hash: ${operationHash}`)
    console.log(`Deployed contract: ${contractAddress}`)

    // Seems like sometimes Node's mempools run a little slow.
    await Utils.sleep(OPERATION_DELAY_SECS)

    return {
      operationHash,
      contractAddress,
    }
  } catch (e) {
    console.log('Caught exception, retrying...')
    console.log(e)
    await Utils.sleep(OPERATION_DELAY_SECS)

    return deployContract(
      contractSource,
      storage,
      keystore,
      counter,
      nodeAddress,
      isMicheline,
    )
  }
}
