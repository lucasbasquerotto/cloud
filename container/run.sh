#!/bin/bash
set -eou pipefail

RED='\033[0;31m'
NC='\033[0m' # No Color

function error {
	msg="$(date '+%F %T') - ${BASH_SOURCE[0]}: line ${BASH_LINENO[0]}: ${*}"
	>&2 echo -e "${RED}${msg}${NC}"
	exit 2
}

args=()
debug=()

# shellcheck disable=SC2214
while getopts ':fp-:' OPT; do
	if [ "$OPT" = "-" ]; then   # long option: reformulate OPT and OPTARG
		OPT="${OPTARG%%=*}"       # extract long option name
		OPTARG="${OPTARG#$OPT}"   # extract long option argument (may be empty)
		OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
	fi
	case "$OPT" in
		f|fast ) fast="true"; args+=( "--fast" );;
		p|prepare ) prepare="true"; args+=( "--prepare" );;
		debug ) debug=( "-vvvvv" ); args+=( "--debug" );;
		??* ) break;;  # long option
		\? )  break;;  # short option
	esac
done
shift $((OPTIND-1))

if [ "${fast:-}" = 'true' ]; then
	echo "[cloud] skipping prepare project (fast)..."
else
	vault=()

	vault_file="/main/secrets/ctl/vault"

	if [ -f "$vault_file" ]; then
		vault=( '--vault-id' "$vault_file" )
	elif [ "${FORCE_VAULT:-}" = 'true' ]; then
		vault=( '--vault-id' 'cloud@prompt')
	fi

	cd /usr/main/ansible

    prepare_args=()

    if [ "${prepare:-}" = 'true' ]; then
        prepare_args=( "${@}" )
    fi

	# Prepare the cloud contexts
	ANSIBLE_CONFIG=/usr/main/ansible/ansible.cfg ansible-playbook \
		${prepare_args[@]+"${prepare_args[@]}"} \
		${vault[@]+"${vault[@]}"} \
		${debug[@]+"${debug[@]}"} \
		prepare.yml || error "[error] prepare ctxs"
fi

# Execute the cloud contexts
bash /main/files/cloud/run-ctxs \
	${args[@]+"${args[@]}"} "${@}" \
	|| error "[error] run-ctxs"
