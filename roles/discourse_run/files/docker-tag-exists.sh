REGISTRY_API_BASE_URL="$1"
REPOSITORY="$2"
VERSION="$3"
UNAME="$4"
UPASS="$5"

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