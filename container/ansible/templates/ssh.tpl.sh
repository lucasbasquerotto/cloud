#!/bin/bash
#shellcheck disable=SC2214
set -euo pipefail

GRAY='\033[0;90m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function info {
	msg="$(date '+%F %T') - ${*}"
	>&2 echo -e "${GRAY}${msg}${NC}"
}

function error {
	msg="$(date '+%F %T') - ${BASH_SOURCE[0]}: line ${BASH_LINENO[0]}: ${*}"
	>&2 echo -e "${RED}${msg}${NC}"
	exit 2
}

while getopts ':c:n:i:-:' OPT; do
	if [ "$OPT" = "-" ]; then    # long option: reformulate OPT and OPTARG
		OPT="${OPTARG%%=*}"      # extract long option name
		OPTARG="${OPTARG#$OPT}"  # extract long option argument (may be empty)
		OPTARG="${OPTARG#=}"     # if long option argument, remove assigning `=`
	fi
	case "$OPT" in
		c|ctx ) arg_ctx="${OPTARG:-}";;
		n|node ) arg_node="${OPTARG:-}";;
		i|idx ) arg_idx="${OPTARG:-}";;
		\? ) error "[error] unknown short option: -${OPTARG:-}";;
		?* ) error "[error] unknown long option: --${OPT:-}";;
	esac
done
shift $((OPTIND-1))

function get_hosts_block {
    hosts_file="${1:-}"
    node_name="${2:-}"
    is_vars="${3:-}"
    block_name="$node_name"

    if [ "$is_vars" = 'true' ]; then
        block_name="${node_name}:vars"
    fi

    result="$(
        awk '
            function my_print() {
                if (SUB) {
                    if (!match($0, /^[ ]*#/))
                    print $0
                }
            }
            match($0, /^\[.*$/             ) { if (SUB) { SKIP=1; exit } }
            match($0, /^\['"$block_name"'\]/) { SUB=1 }
            !/(^\[)|(^[ ]*$)/ { my_print() }
        ' "$hosts_file"
    )"

    echo "$result"
}

{% if (project_ssh_default_ctx | default('')) != '' %}
    {% if not (project_ssh_default_ctx in (project_ssh_ctxs | default([]))) %}
        {% set error = {} %}
        {{ error['error.invalid_ctx.' + project_ssh_default_ctx] }}
    {% endif %}
    {% set ssh_default_ctx = project_ssh_default_ctx %}
{% else %}
    {% if (project_ssh_ctxs | default([]) | length) == 1 %}
        {% set ssh_default_ctx = project_ssh_ctxs[0] %}
    {% endif %}
{% endif %}
{% if (project_ssh_default_node | default('')) != '' %}
    {% if not (project_ssh_default_node in (project_ssh_nodes | default([]))) %}
        {% set error = {} %}
        {{ error['error.invalid_node.' + project_ssh_default_node] }}
    {% endif %}
    {% set ssh_default_node = project_ssh_default_node %}
{% else %}
    {% if (project_ssh_nodes | default([]) | length) == 1 %}
        {% set ssh_default_node = project_ssh_nodes[0] %}
    {% endif %}
{% endif %}

project_secrets_cloud_dir={{ project_secrets_cloud_dir | quote }}
ssh_default_ctx={{ ssh_default_ctx | default('') | quote }}
ssh_default_node={{ ssh_default_node | default('') | quote }}

ctx_name="${arg_ctx:-$ssh_default_ctx}"
node_name="${arg_node:-$ssh_default_node}"
instance_index="${arg_idx:-1}"

if [ -z "$ctx_name" ]; then
    error "ctx not defined for ssh (use parameter --ctx or define a default context)"
fi

if [ -z "$node_name" ]; then
    error "node not defined for ssh (use parameter --node or define a default node)"
fi

hosts_file="$project_secrets_cloud_dir/ctxs/$ctx_name/hosts"

if [ ! -f "$hosts_file" ]; then
    msg_aux="maybe the context (ctx) is wrong, or the preparation step was not done"
    error "[error] the hosts file $hosts_file doesn't exist ($msg_aux)"
fi

hosts="$(get_hosts_block "$hosts_file" "$node_name")"

vars="$(get_hosts_block "$hosts_file" "$node_name" 'true')"

host="$(echo "$hosts" | grep "instance_index=$instance_index " | tail -n 1 || :)"

if [ -z "$host" ]; then
    msg="No line (host) in the hosts file ($hosts_file) with the node type '$node_name'"

	if [[ "$instance_index" -gt 1 ]]; then
    	msg="$msg in the index $instance_index (starting in 1)"
	fi

    echo -e "${RED}${msg}${NC}"
    exit 1
fi

vars_user="$(echo "$vars" | sed -n -e 's/^ansible_user=//p' | awk '{ print $1 }')"
vars_host="$(echo "$vars" | sed -n -e 's/^ansible_host=//p' | awk '{ print $1 }')"
vars_key_file="$(echo "$vars" | sed -n -e 's/^ansible_ssh_private_key_file=//p' | awk '{ print $1 }')"

ansible_user="$(echo "$host" | sed -n -e 's/^.*ansible_user=//p' | awk '{ print $1 }')"
ansible_host="$(echo "$host" | sed -n -e 's/^.*ansible_host=//p' | awk '{ print $1 }')"
key_file="$(echo "$host" | sed -n -e 's/^.*ansible_ssh_private_key_file=//p' | awk '{ print $1 }')"

ansible_user="${ansible_user:-$vars_user}"
ansible_host="${ansible_host:-$vars_host}"
key_file="${key_file:-$vars_key_file}"

if [ -z "$key_file" ]; then
    echo "ssh $ansible_user@$ansible_host"
    ssh "$ansible_user@$ansible_host"
else
    echo "ssh -i $key_file $ansible_user@$ansible_host"
    ssh -i "$key_file" "$ansible_user@$ansible_host"
fi
