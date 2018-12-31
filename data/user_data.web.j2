#!/bin/bash
set -euo pipefail

########################
### SCRIPT VARIABLES ###
########################

# Docker version
DOCKER_CE_VERSION="{{ docker_ce_version | default('5:18.09.0~3-0~ubuntu-bionic') }}"

# Name of the user to create and grant sudo privileges
USERNAME="{{ host_user }}"

# Password of the user to create and grant sudo privileges
PASSWORD="{{ host_pass }}"

# Additional public keys to add to the new sudo user
# OTHER_PUBLIC_KEYS_TO_ADD=(
#	"ssh-rsa AAAAB..."
#	"ssh-rsa AAAAB..."
# )
OTHER_PUBLIC_KEYS_TO_ADD=( 
{% for item in host_ssh_public_keys %}
	"{{ item }}" 
{% endfor %}
)

####################
### SCRIPT LOGIC ###
####################

# Add sudo user and grant privileges
useradd --create-home --shell "/bin/bash" --groups sudo "${USERNAME}"

# Check whether the root account has a real password set
encrypted_root_pw="$(grep root /etc/shadow | cut --delimiter=: --fields=2)"

if [ -z "${PASSWORD}" ]; then
	if [ "${encrypted_root_pw}" != "*" ]; then
		# Transfer auto-generated root password to user if present
		# and lock the root account to password-based access
		echo "${USERNAME}:${encrypted_root_pw}" | chpasswd --encrypted
		passwd --lock root
	else
		# Delete invalid password for user if using keys so that a new password
		# can be set without providing a previous value
		passwd --delete "${USERNAME}"
	fi

	# Expire the sudo user's password immediately to force a change
	chage --lastday 0 "${USERNAME}"
else
	passwd --delete "${USERNAME}"
	echo "$USERNAME:$PASSWORD" | chpasswd

	echo "New password defined for $USERNAME" >> "/var/log/setup.log"

	if [ "${encrypted_root_pw}" != "*" ]; then
		passwd --lock root
	fi
fi

# Create SSH directory for sudo user
home_directory="$(eval echo ~${USERNAME})"
mkdir --parents "${home_directory}/.ssh"

# Add additional provided public keys
for pub_key in "${OTHER_PUBLIC_KEYS_TO_ADD[@]}"; do
	echo "${pub_key}" >> "${home_directory}/.ssh/authorized_keys"
done

# Adjust SSH configuration ownership and permissions
chmod 0700 "${home_directory}/.ssh"
chmod 0600 "${home_directory}/.ssh/authorized_keys"
chown --recursive "${USERNAME}":"${USERNAME}" "${home_directory}/.ssh"

# Disable root SSH login with password
sed --in-place 's/^PermitRootLogin.*/PermitRootLogin prohibit-password/g' /etc/ssh/sshd_config
if sshd -t -q; then
	systemctl restart sshd
fi

# Add exception for SSH and then enable UFW firewall
# ufw allow 22
# ufw allow 6443
# ufw --force enable

apt autoremove -y

echo "Main logic finished" >> "/var/log/setup.log"

########################
###   ANSIBLE HOST   ###
########################

echo "Preparing Ansible Host..." >> "/var/log/setup.log"

apt update
apt install -y python

echo "Ansible Host Prepared" >> "/var/log/setup.log"

########################
###      DOCKER      ###
########################

echo "Preparing Docker Installation..." >> "/var/log/setup.log"

# First, update your existing list of packages
apt update

# Next, install a few prerequisite packages which let apt use packages over HTTPS
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Then add the GPG key for the official Docker repository to your system
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

# Add the Docker repository to APT sources
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable" -y

# Next, update the package database with the Docker packages from the newly added repo
apt update

# Finally, install Docker
apt install -y docker-ce=$DOCKER_CE_VERSION

echo "Docker Installed" >> "/var/log/setup.log"

########################
###       END        ###
########################

echo "Setup Finished" >> "/var/log/setup.log"
