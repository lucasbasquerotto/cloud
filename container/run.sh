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

last_index=1

# shellcheck disable=SC2214
while getopts ':fp-:' OPT; do
	last_index="$OPTIND"
	if [ "$OPT" = "-" ]; then     # long option: reformulate OPT and OPTARG
		OPT="${OPTARG%%=*}"       # extract long option name
		OPTARG="${OPTARG#$OPT}"   # extract long option argument (may be empty)
		OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
	fi
	case "$OPT" in
		f|fast ) fast="true"; args+=( "--fast" );;
		p|prepare ) prepare="true"; args+=( "--prepare" );;
		debug ) debug=( "-vvvvv" ); args+=( "--debug" );;
		project-dir ) project_dir=${OPTARG:-};;
		\? ) error "[error] unknown short option: -${OPTARG:-}";;
		?* ) error "[error] unknown long option: --${OPT:-}";;
	esac
done

if [ "$last_index" != "$OPTIND" ]; then
	args+=( "--" );
fi

shift $((OPTIND-1))

if [ -z "${project_dir:-}" ]; then
	error "[error] project-dir not specified"
fi

if [ "${fast:-}" = 'true' ]; then
	echo "[cloud] skipping prepare project (fast)..."
else
	vault=()

	vault_file="$project_dir/secrets/ctl/vault"

	if [ -f "$vault_file" ]; then
		vault=( '--vault-id' "$vault_file" )
	elif [ "${FORCE_VAULT:-}" = 'true' ]; then
		vault=( '--vault-id' 'cloud@prompt')
	fi

	cd /usr/main/ansible

    prepare_args=()
	skip=''

    if [ "${prepare:-}" = 'true' ]; then
		if [ "${1:-}" = "--skip" ]; then
			skip='true';
			shift;
		else
			for arg in "$@"; do
				shift;

				if [ "$arg" = "--" ]; then
					break;
				fi

				prepare_args+=( "$arg" )
			done
		fi
    fi

	if [ "$skip" = "true" ]; then
		echo "[cloud] skipping prepare project (skip)..."
	else
		# Prepare the cloud contexts
		ANSIBLE_CONFIG=/usr/main/ansible/ansible.cfg ansible-playbook \
			${vault[@]+"${vault[@]}"} \
			${debug[@]+"${debug[@]}"} \
			prepare.yml \
			--extra-vars "env_project_dir=$project_dir" \
			${prepare_args[@]+"${prepare_args[@]}"} \
			|| error "[error] prepare ctxs"
	fi
fi

# Execute the cloud contexts
bash "$project_dir/files/cloud/run-ctxs" \
	${args[@]+"${args[@]}"} "${@}" \
	|| error "[error] run-ctxs"
