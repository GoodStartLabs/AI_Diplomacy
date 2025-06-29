#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Setting env variables
if [ -z ${NVM_DIR+x} ]; then
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
fi

# Downloading and install NVM
if [ ! -d "$HOME/.nvm" ]; then
    curl -sL https://raw.githubusercontent.com/creationix/nvm/v0.33.8/install.sh -o install_nvm.sh
    bash install_nvm.sh
    rm -Rf install_nvm.sh
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    nvm install v8.11.2
    echo "Done installing NVM v0.33.8 and NodeJS v8.11.2"
else
    echo "NVM is already installed in ~/.nvm"
fi

# Installing dependencies
if [ -d "$DIR/diplomacy/web/" ]; then
    cd $DIR/diplomacy/web
    rm -Rf node_modules
    npm install .
    npm install . --only=dev
    cd -
else
    echo "Folder $DIR/diplomacy/web does not exists. Cannot install package.json"
fi
