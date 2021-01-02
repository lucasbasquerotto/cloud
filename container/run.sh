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
while getopts ':fnps-:' OPT; do
	last_index="$OPTIND"
	if [ "$OPT" = "-" ]; then     # long option: reformulate OPT and OPTARG
		OPT="${OPTARG%%=*}"       # extract long option name
		OPTARG="${OPTARG#$OPT}"   # extract long option argument (may be empty)
		OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
	fi
	case "$OPT" in
		f|force ) force='true'; args+=( "--force" );;
		n|next ) next='true';;
		p|prepare ) prepare='true'; args+=( "--prepare" );;
		s|fast ) fast='true'; args+=( "--fast" );;
		debug ) debug=( "-vvvvv" ); args+=( "--debug" );;
		project-dir ) project_dir=${OPTARG:-};;
		\? ) error "[error] unknown short option: -${OPTARG:-}";;
		?* ) error "[error] unknown long option: --${OPT:-}";;
	esac
done

shift $((OPTIND-1))

if [ -z "${project_dir:-}" ]; then
	error "[error] project-dir not specified"
fi

if [ "${next:-}" = 'true' ] && [ "${prepare:-}" = 'true' ]; then
	error "[error] next and prepare shouldn't be both true"
fi

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

if [ "${next:-}" = 'true' ]; then
	next_opt=''
	OPTIND=1

	# shellcheck disable=SC2214
	while getopts ':-:' OPT; do
		last_index="$OPTIND"
		if [ "$OPT" = "-" ]; then     # long option: reformulate OPT and OPTARG
			OPT="${OPTARG%%=*}"       # extract long option name
			OPTARG="${OPTARG#$OPT}"   # extract long option argument (may be empty)
			OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
		fi
		case "$OPT" in
			end ) next_opt='true'; args+=( "--end" );;
			ssh ) next_opt='true'; ssh='true'; break;;
			\? ) error "[error] unknown next short option: -${OPTARG:-}";;
			?* ) error "[error] unknown next long option: --${OPT:-}";;
		esac
	done

	shift $((OPTIND-1))

	if [ "${next_opt:-}" != 'true' ]; then
		msg_aux="ssh, end"
		error "[error] no option specified using the next argument (options: $msg_aux)"
	fi
fi

if [ "${ssh:-}" = 'true' ] && [ "${end:-}" = 'true' ]; then
	error "[error] both end and ssh options are defined (should me at most one of them)"
fi

skip_main=''

if [ "${ssh:-}" = 'true' ]; then
	if [ "${fast:-}" = 'true' ]; then
		skip_main='true'
	else
		args+=( "--prepare" )
	fi
fi

if [ "$last_index" != "$OPTIND" ]; then
	args+=( "--" );
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

	if [ "$skip" = 'true' ]; then
		echo "[cloud] skipping prepare project (skip)..."
	else
		# Prepare the cloud contexts
		ANSIBLE_CONFIG=/usr/main/ansible/ansible.cfg ansible-playbook \
			${vault[@]+"${vault[@]}"} \
			${debug[@]+"${debug[@]}"} \
			-i hosts \
			prepare.yml \
			--extra-vars "env_project_dir=$project_dir" \
			${prepare_args[@]+"${prepare_args[@]}"} \
			|| error "[error] prepare ctxs"
	fi
fi

last_commit=''
can_change_commit=''
commit_dir="$project_dir/files/cloud/commit"

if [ "${prepare:-}" != 'true' ] && [ "${next:-}" != 'true' ]; then
	can_change_commit='true'
fi

if [ "$can_change_commit" = 'true' ]; then
	if [ -f "$commit_dir/backup" ]; then
		last_commit="$(cat "$commit_dir/backup")"
	fi

	# shellcheck source=./commit.sample.sh
	. "$commit_dir/current"
fi

diff_commit=''

if [ "$last_commit" = '' ] || [ "$last_commit" != "${commit:-}" ]; then
	diff_commit='true'
fi

if [ "${skip_main:-}" = 'true' ]; then
	echo "[cloud] skipping the cloud contexts execution (skip main)..."
elif [ "${force:-}" = 'true' ] || [ "$diff_commit" = 'true' ]; then
	# Execute the cloud contexts
	bash "$project_dir/files/cloud/run-ctxs" \
		${args[@]+"${args[@]}"} "${@}" \
		|| error "[error] run-ctxs"

	if [ "$can_change_commit" = 'true' ]; then
		echo "${commit:-}" > "$commit_dir/backup"
	fi
else
	echo "[cloud] skipping the cloud contexts execution (same commit)..."
fi

if [ "${ssh:-}" = 'true' ]; then
	# Connect through ssh
	bash "$project_dir/files/cloud/ssh" "${@}" || error "[error] ssh"
fi