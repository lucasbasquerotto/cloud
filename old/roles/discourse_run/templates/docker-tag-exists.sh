#!/bin/bash
set -e

REGISTRY_API_BASE_URL="{{ discourse_run_tpl_registry_api_base_url }}"
REPOSITORY="{{ discourse_run_tpl_repository }}"
VERSION="{{ discourse_run_tpl_version }}"
UNAME="{{ discourse_run_tpl_uname }}"
UPASS="{{ discourse_run_tpl_upass }}"

function docker_tag_exists() {
    TOKEN=$(curl -s -H "Content-Type: application/json" -X POST -d '{"username": "'${UNAME}'", "password": "'${UPASS}'"}' "${REGISTRY_API_BASE_URL}/users/login/" | jq -r .token)
    EXISTS=$(curl -s -H "Authorization: JWT ${TOKEN}" "${REGISTRY_API_BASE_URL}/repositories/$1/tags/?page_size=10000" | jq -r "[.results | .[] | .name == \"$2\"] | any")
    test $EXISTS = true
}

if docker_tag_exists "${REPOSITORY}" "${VERSION}"; then
    echo 1
else 
    echo 0
fi