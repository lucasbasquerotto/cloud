#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
NC='\033[0m' # No Color

function error {
	msg="$(date '+%F %T') - ${BASH_SOURCE[0]}: line ${BASH_LINENO[0]}: ${*}"
	>&2 echo -e "${RED}${msg}${NC}"
	exit 2
}

title="{{ project_run_ctxs_title | quote }}"

{% if (project_run_ctxs_list | default([]) | length) > 0 %}
{% for ctx in project_run_ctxs_list %}
{% set run_file = project_run_ctxs_env.main[ctx].run_file | default('run') %}
. "{{ (project_run_ctx_cloud_dir + '/ctxs/' + ctx + '/vars.sh') | quote }}"
bash "$repo_run_file" "$ctx_dir" "${@}" || error "[error] $title ($ctx)"
{% endfor %}
{% endif %}
