import { BigNumber } from 'bignumber.js'
import { LogLevelDesc } from 'loglevel'
import { scaleTokenAmount } from './utils'

/** Global configuration applied to all deploys. */

/** Number of tokens to mint, as an integer. This number is scaled automatically */
const NUM_TOKENS = new BigNumber('1000000')

/** Log level for deploy. */
const LOG_LEVEL: LogLevelDesc = 'info'

/**
 * Computed properties - do not modify this logic.
 */
const CONFIG = {
  TOKENS_TO_MINT: scaleTokenAmount(NUM_TOKENS),
  LOG_LEVEL,
}
export default CONFIG
