#!/bin/bash
# Syntax: ./run_tests               -- Run tests in parallel across CPUs
#         ./run_tests <nb_cores>    -- Run tests in parallel across this number of CPUs
#         ./run_tests 0             -- Only runs the pylint tests
export PYTHONIOENCODING=utf-8
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FAILED=0

# Running pytest
if [ "${1:-auto}" != "0" ]; then
    pytest -v --forked -n "${1:-auto}" diplomacy || FAILED=1
fi

# Running pylint
echo ""
echo "------------------------------"
echo "         PYLINT TESTS         "
echo "------------------------------"
echo ""
find diplomacy -name "*.py" ! -name 'zzz_*.py' ! -name '_*.py' -exec pylint '{}' + || FAILED=1

# Running sphinx
echo ""
echo "------------------------------"
echo "         SPHINX TESTS         "
echo "------------------------------"
echo ""
cd $DIR/docs
make clean || FAILED=1
make html || FAILED=1
cd -

# Running eslint
echo ""
echo "------------------------------"
echo "         ESLINT TESTS         "
echo "------------------------------"
echo ""
if [ -f "$DIR/diplomacy/web/node_modules/.bin/eslint" ]; then
    if [ -z ${NVM_DIR+x} ]; then
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    fi
    cd $DIR/diplomacy/web/
    node_modules/.bin/eslint --ext js,jsx . || FAILED=1
    npm run build || FAILED=1
    cd -
else
    echo "Skipping ESLint. Make sure NVM and NodeJS are installed first."
fi

# Exiting
if [[ "$FAILED" -eq 1 ]]; then
    echo "*** TESTS FAILED ***"
    exit 1
else
    echo "All tests passed."
    exit 0
fi
