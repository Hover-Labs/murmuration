#!/usr/bin/env bash

set -e -o pipefail

echo "----------------------------------------"
echo "Compiling Dao Contracts"
echo "----------------------------------------"

# Expected location of SmartPy CLI.
SMART_PY_CLI=~/smartpy-cli/SmartPy.sh

# Output directory
OUT_DIR=./.smartpy_out

# Array of files to compile.
CONTRACTS_ARRAY=(community-fund dao faucet token vesting-vault)

# Ensure we have a SmartPy binary.
if [ ! -f "$SMART_PY_CLI" ]; then
    echo "Fatal: Please install SmartPy CLI at $SMART_PY_CLI" && exit
fi

# Compile a contract.
# Args <contract name, ex: minter> <invocation, ex: MinterContract()> <out dir>
function processContract {
    CONTRACT_NAME=$1
    OUT_DIR=$2
    CONTRACT_IN="${CONTRACT_NAME}.py"
    CONTRACT_OUT="${CONTRACT_NAME}.tz"
    CONTRACT_COMPILED="${CONTRACT_NAME}/step_000_cont_0_contract.tz"

    echo ">> Processing ${CONTRACT_NAME}"

    # Ensure file exists.
    if [ ! -f "$CONTRACT_IN" ]; then
        echo "Fatal: $CONTRACT_IN not found. Running from wrong dir?" && exit
    fi

    # Test
    echo ">>> [1 / 3] Testing ${CONTRACT_NAME} "
    $SMART_PY_CLI test $CONTRACT_IN $OUT_DIR
    echo ">>> Done"

    echo ">>> [2 / 3] Compiling ${CONTRACT_NAME}"
    $SMART_PY_CLI compile $CONTRACT_IN $OUT_DIR
    echo ">>> Done."

    echo ">>> [3 / 3] Copying Artifacts"
    cp $OUT_DIR/$CONTRACT_COMPILED $CONTRACT_OUT
    echo ">>> Written to ${CONTRACT_OUT}"
}

echo "> [1 / 3] Unit Testing and Compiling Contracts."
for i in ${!CONTRACTS_ARRAY[@]}; do
    echo ">> [$((i + 1)) / ${#CONTRACTS_ARRAY[@]}] Processing ${CONTRACTS_ARRAY[$i]}"
    processContract ${CONTRACTS_ARRAY[$i]} $OUT_DIR
    echo ">> Done."
    echo ""
done
echo "> Compilation Complete."
echo ""

# Remove other artifacts to reduce noise.
echo "> [2 / 2] Cleaning up"
rm -rf $OUT_DIR
echo "> All tidied up."
echo ""

echo "----------------------------------------"
echo "Task complete."
echo "----------------------------------------"
