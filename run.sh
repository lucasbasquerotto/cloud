#!/bin/bash
set -e

GIT_REPO="https://github.com/lucasbasquerotto/ansible-demo.git"

cd ~

rm -rf ansible-demo
rm -rf ansible

git clone "$GIT_REPO"
mkdir ansible
shopt -s dotglob
mv ansible-demo/* ansible/
rm -rf ansible-demo

mkdir -p ~/env
mv -vn ~/ansible/env/env.yml ~/env/env.yml
mv -vn ~/ansible/env/hosts ~/env/hosts

cd ~/ansible/
ansible-playbook main.yml "$@"
