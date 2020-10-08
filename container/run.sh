#!/bin/bash
set -eou pipefail

vault=()

vault_file="/main/secrets/ctl/vault"

if [ -f "$vault_file" ]; then
    vault=( '--vault-id' "$vault_file" )
elif [ "${FORCE_VAULT:-}" = 'true' ]; then
    vault=( '--vault-id' 'cloud@prompt')
fi

cd /usr/main/ansible

ansible-playbook ${vault[@]+"${vault[@]}"} prepare.yml