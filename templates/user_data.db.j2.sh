#!/bin/bash
set -euo pipefail

########################
### SCRIPT VARIABLES ###
########################

# Docker version
MYSQL_VERSION="{{ mysql_version | default('8.0.13-1ubuntu18.04') }}"

# Docker version
MYSQL_PASS="{{ mysql_password }}"

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
###      MYSQL       ###
########################

echo "Installing MySQL..." >> "/var/log/setup.log"

echo "Adding the MySQL Package..." >> "/var/log/setup.log"

cd /tmp

curl -OL https://dev.mysql.com/get/mysql-apt-config_0.8.10-1_all.deb

export DEBIAN_FRONTEND="noninteractive"; 
"echo mysql-apt-config mysql-apt-config/select-server select mysql-8.0" | debconf-set-selections
sudo -E dpkg -i mysql-apt-config*

rm mysql-apt-config*

echo "MySQL Package Added" >> "/var/log/setup.log"

apt update

debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_PASS"
debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_PASS"
debconf-set-selections <<< "mysql-community-server mysql-community-server/root-pass password $MYSQL_PASS"
debconf-set-selections <<< "mysql-community-server mysql-community-server/re-root-pass password $MYSQL_PASS"
apt-get install -y mysql-server="$MYSQL_VERSION"

echo "MySQL Installed" >> "/var/log/setup.log"

########################
###       END        ###
########################

echo "Setup Finished" >> "/var/log/setup.log"
