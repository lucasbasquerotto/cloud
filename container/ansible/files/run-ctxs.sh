#!/bin/bash
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
NC='\033[0m' # No Color

function error {
	msg="$(date '+%F %T') - ${BASH_SOURCE[0]}: line ${BASH_LINENO[0]}: ${*}"
	>&2 echo -e "${RED}${msg}${NC}"
	exit 2
}

# shellcheck source=./vars.sample.sh
. "$dir/vars.sh"

var_project_title="$project_title"
var_project_ctxs="$project_ctxs"
var_project_files_cloud_dir="$project_files_cloud_dir"

if [ -n "$var_project_ctxs" ]; then
	IFS=',' read -r -a tmp <<< "$var_project_ctxs"
	arr=("${tmp[@]}")

	for ctx in "${arr[@]}"; do
		# shellcheck source=./vars.ctx.sample.sh
		. "${var_project_files_cloud_dir}/ctxs/${ctx}/vars.sh"

		bash "$repo_run_file" "$ctx_dir" "${@}" \
			|| error "[error] $var_project_title ($ctx)"
	done
fi
