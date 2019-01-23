#!/bin/bash
# shellcheck disable=SC1083,SC2129
set -euo pipefail

########################
### SCRIPT VARIABLES ###
########################

# MySQL version
MYSQL_MAJOR=8.0
MYSQL_VERSION="{{ mysql_version | default('8.0.13-1ubuntu18.04') }}"

# MySQL password
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
		echo "${USERNAME}:${encrypted_root_pw}" | chpasswd --encrypted
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
fi

if [ "${encrypted_root_pw}" != "*" ]; then
	# lock the root account to password-based access
	# almost equivalent to: $ passwd --lock root
	# avoids errors like "You are required to change your password immediately (root enforced)"
	sed -i 's/^root:.*$/root:*:16231:0:99999:7:::/' /etc/shadow
fi

# Create SSH directory for sudo user
home_directory="/home/${USERNAME}"
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

#echo "Adding the MySQL Package..." >> "/var/log/setup.log"

#cd /tmp

#curl -OL https://dev.mysql.com/get/mysql-apt-config_0.8.10-1_all.deb

#export DEBIAN_FRONTEND="noninteractive"; 
#echo "mysql-apt-config mysql-apt-config/select-server select mysql-8.0" | debconf-set-selections
##sudo -E dpkg -i mysql-apt-config*
#dpkg -i mysql-apt-config*

#rm mysql-apt-config*

#echo "MySQL Package Added" >> "/var/log/setup.log"

#apt update

#debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_PASS"
#debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_PASS"
#debconf-set-selections <<< "mysql-community-server mysql-community-server/root-pass password $MYSQL_PASS"
#debconf-set-selections <<< "mysql-community-server mysql-community-server/re-root-pass password $MYSQL_PASS"
#apt-get install -y mysql-server="$MYSQL_VERSION"
##mysql installation You are required to change your password immediately (root enforced)

#echo "MySQL Installed" >> "/var/log/setup.log"

{
	echo "mysql-apt-config mysql-apt-config/repo-codename select trusty" \
	echo "mysql-apt-config mysql-apt-config/repo-distro select ubuntu" \
	echo "mysql-apt-config mysql-apt-config/repo-url string http://repo.mysql.com/apt/" \
	echo "mysql-apt-config mysql-apt-config/select-preview select " \
	echo "mysql-apt-config mysql-apt-config/select-product select Ok" \
	echo "mysql-apt-config mysql-apt-config/select-server select mysql-$MYSQL_MAJOR" \
	echo "mysql-apt-config mysql-apt-config/select-tools select " \ 
	echo "mysql-apt-config mysql-apt-config/unsupported-platform select abort" \

	echo "mysql-community-server mysql-community-server/data-dir select $MYSQL_PASS;" \
	echo "mysql-community-server mysql-community-server/root-pass password $MYSQL_PASS;" \
	echo "mysql-community-server mysql-community-server/re-root-pass password $MYSQL_PASS;" \
	echo "mysql-community-server mysql-community-server/remove-test-db select false;" \
} | debconf-set-selections

echo "MySQL debconf-set-selections" >> "/var/log/setup.log"

cd /tmp
curl -OL https://dev.mysql.com/get/mysql-apt-config_0.8.10-1_all.deb

export DEBIAN_FRONTEND="noninteractive"; 
dpkg -i mysql-apt-config*

echo "MySQL Repo" >> "/var/log/setup.log"

apt-get update 
apt-get install -y mysql-server="$MYSQL_VERSION"
#apt-get install -y \
#	mysql-community-client="${MYSQL_VERSION}" \
#	mysql-community-server-core="${MYSQL_VERSION}" 

echo "MySQL Installed" >> "/var/log/setup.log"

rm -rf /var/lib/apt/lists/*
rm -rf /var/lib/mysql 

mkdir -p /var/lib/mysql /var/run/mysqld 
chown -R mysql:mysql /var/lib/mysql /var/run/mysqld 

echo "MySQL Finished" >> "/var/log/setup.log"

########################
###       END        ###
########################

echo "Setup Finished" >> "/var/log/setup.log"
