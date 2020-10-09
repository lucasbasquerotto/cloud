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

# shellcheck disable=SC2214
while getopts ':-:' OPT; do
	if [ "$OPT" = "-" ]; then   # long option: reformulate OPT and OPTARG
		OPT="${OPTARG%%=*}"       # extract long option name
		OPTARG="${OPTARG#$OPT}"   # extract long option argument (may be empty)
		OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
	fi
	case "$OPT" in
		fast ) arg_fast="true"; args+=( "$OPT" );;
		??* ) [ -z "$OPTARG" ] \
			&& args+=( "$OPT" ) \
			|| args+=( "$OPT=$OPTARG" ) ;;  # bad long option
		\? )  exit 2 ;;  # bad short option (error reported via getopts)
	esac
done
shift $((OPTIND-1))


if [ "${arg_fast:-}" = 'true' ]; then
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

	# Prepare the cloud contexts
	ansible-playbook ${vault[@]+"${vault[@]}"} prepare.yml || error "[error] prepare"
fi

# Execute the cloud contexts
/main/files/cloud/run-ctxs || error "[error] run-ctxs"
