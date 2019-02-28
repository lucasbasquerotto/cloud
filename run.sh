#!/bin/bash
set -e

REPO_NAME="ansible-docker"
GIT_REPO="https://github.com/lucasbasquerotto/$REPO_NAME.git"

cd ~

rm -rf "$REPO_NAME"
rm -rf ansible

git clone "$GIT_REPO"
mkdir ansible
shopt -s dotglob
mv "$REPO_NAME"/* ansible/
rm -rf "$REPO_NAME"

mkdir -p ~/env
mv -vn ~/ansible/env/env.yml ~/env/env.yml
mv -vn ~/ansible/env/hosts ~/env/hosts

# cd ~/ansible/
# ansible-playbook main.yml "$@"
