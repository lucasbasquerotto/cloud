#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

##
## Make sure only root can run our script
##
check_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Please sudo or log in as root first." 1>&2
    exit 1
  fi
}

##
## Check whether a connection to HOSTNAME ($1) on PORT ($2) is possible
##
connect_to_port () {
  HOST="$1"
  PORT="$2"
  VERIFY=`date +%s | sha256sum | base64 | head -c 20`
  echo -e "HTTP/1.1 200 OK\n\n $VERIFY" | nc -w 4 -l -p $PORT >/dev/null 2>&1 &
  if curl --proto =http -s $HOST:$PORT --connect-timeout 3 | grep $VERIFY >/dev/null 2>&1
  then
      return 0
  else
    curl --proto =http -s localhost:$PORT >/dev/null 2>&1
    return 1
  fi
}

check_IP_match () {
  HOST="$1"
  echo
  echo Checking your domain name . . .

  if connect_to_port $HOST 443
  then
    echo
    echo "Connection to $HOST succeeded."
  else
    echo WARNING:: This server does not appear to be accessible at $HOST:443.
    echo

    if connect_to_port $HOST 80
    then
      echo A connection to port 80 succeeds, however.
      echo This suggests that your DNS settings are correct,
      echo but something is keeping traffic to port 443 from getting to your server.
      echo Check your networking configuration to see that connections to port 443 are allowed.
    else
      echo "A connection to http://$HOST (port 80) also fails."
      echo
      echo This suggests that $HOST resolves to the wrong IP address
      echo or that traffic is not being routed to your server.
    fi

    echo
    echo Google: \"open ports YOUR CLOUD SERVICE\" for information for resolving this problem.
    echo
    echo You should probably answer \"n\" at the next prompt and disable Let\'s Encrypt.
    echo
    echo This test might not work for all situations,
    echo so if you can access Discourse at http://$HOST, you might try anyway.
    sleep 3
  fi
}

##
## Do we have docker?
##
check_docker () {
  docker_path=`which docker.io || which docker`

  if [ -z $docker_path ]; then
    echo "Error: Docker not installed." 1>&2
    exit 1
  fi
}

##
## What are we running on
##
check_OS() {
  echo `uname -s`
}

##
## OS X available memory
##
check_osx_memory() {
  echo `free -m | awk '/Mem:/ {print $2}'`
}

##
## Linux available memory
##
check_linux_memory() {
  echo `free -g --si | awk ' /Mem:/  {print $2} '`
}

##
## Do we have enough memory and disk space for Discourse?
##
check_disk_and_memory() {
  os_type=$(check_OS)
  avail_mem=0

  if [ "$os_type" == "Darwin" ]; then
    avail_mem=$(check_osx_memory)
  else
    avail_mem=$(check_linux_memory)
  fi

  if [ "$avail_mem" -lt 1 ]; then
    echo "WARNING: Discourse requires 1GB RAM to run. This system does not appear"
    echo "to have sufficient memory."
    echo
    echo "Your site may not work properly, or future upgrades of Discourse may not"
    echo "complete successfully."
    exit 1
  fi

  if [ "$avail_mem" -le 2 ]; then
    total_swap=`free -g --si | awk ' /Swap:/  {print $2} '`

    if [ "$total_swap" -lt 2 ]; then
      echo "WARNING: Discourse requires at least 2GB of swap when running with 2GB of RAM"
      echo "or less. This system does not appear to have sufficient swap space."
      echo
      echo "Without sufficient swap space, your site may not work properly, and future"
      echo "upgrades of Discourse may not complete successfully."
      echo
      echo "Ctrl+C to exit or wait 5 seconds to have a 2GB swapfile created."
      sleep 5

      ##
      ## derived from https://meta.discourse.org/t/13880
      ##
      install -o root -g root -m 0600 /dev/null /swapfile
      dd if=/dev/zero of=/swapfile bs=1k count=2048k
      mkswap /swapfile
      swapon /swapfile
      echo "/swapfile       swap    swap    auto      0       0" | tee -a /etc/fstab
      sysctl -w vm.swappiness=10
      echo 'vm.swappiness = 10' > /etc/sysctl.d/30-discourse-swap.conf

      total_swap=`free -g --si | awk ' /Swap:/ {print $2} '`

      if [ "$total_swap" -lt 2 ]; then
        echo "Failed to create swap: are you root? Are you running on real hardware, or a fully virtualized server?"
        exit 1
      fi
    fi
  fi

  free_disk="$(df /var | tail -n 1 | awk '{print $4}')"

  if [ "$free_disk" -lt 5000 ]; then
    echo "WARNING: Discourse requires at least 5GB free disk space. This system"
    echo "does not appear to have sufficient disk space."
    echo
    echo "Insufficient disk space may result in problems running your site, and"
    echo "may not even allow Discourse installation to complete successfully."
    echo
    echo "Please free up some space, or expand your disk, before continuing."
    echo
    echo "Run \`apt-get autoremove && apt-get autoclean\` to clean up unused"
    echo "packages and \`./launcher cleanup\` to remove stale Docker containers."
    exit 1
  fi
}


##
## If we have lots of RAM or lots of CPUs, bump up the defaults to scale better
##
scale_ram_and_cpu() {
  local changelog=/tmp/changelog.$PPID

  # grab info about total system ram and physical (NOT LOGICAL!) CPU cores
  avail_gb=0
  avail_cores=0
  os_type=$(check_OS)

  if [ "$os_type" == "Darwin" ]; then
    avail_gb=$(check_osx_memory)
    avail_cores=`sysctl hw.ncpu | awk '/hw.ncpu:/ {print $2}'`
  else
    avail_gb=$(check_linux_memory)
    avail_cores=$((`awk '/cpu cores/ {print $4;exit}' /proc/cpuinfo`*`sort /proc/cpuinfo | uniq | grep -c "physical id"`))
  fi

  echo "Found ${avail_gb}GB of memory and $avail_cores physical CPU cores"

  # db_shared_buffers: 128MB for 1GB, 256MB for 2GB, or 256MB * GB, max 4096MB
  if [ "$avail_gb" -eq "1" ]
  then
    db_shared_buffers=128
  else
    if [ "$avail_gb" -eq "2" ]
    then
      db_shared_buffers=256
    else
      db_shared_buffers=$(( 256 * $avail_gb ))
    fi
  fi

  db_shared_buffers=$(( db_shared_buffers < 4096 ? db_shared_buffers : 4096 ))

  sed -i -e "s/^  #\?db_shared_buffers:.*/  db_shared_buffers: \"${db_shared_buffers}MB\"/w $changelog" $data_file

  if [ -s $changelog ]
  then
    echo "setting db_shared_buffers = ${db_shared_buffers}MB"
    rm $changelog
  fi

  # UNICORN_WORKERS: 2 * GB for 2GB or less, or 2 * CPU, max 8
  if [ "$avail_gb" -le "2" ]
  then
    unicorn_workers=$(( 2 * $avail_gb ))
  else
    unicorn_workers=$(( 2 * $avail_cores ))
  fi

  unicorn_workers=$(( unicorn_workers < 8 ? unicorn_workers : 8 ))

  sed -i -e "s/^  #\?UNICORN_WORKERS:.*/  UNICORN_WORKERS: ${unicorn_workers}/w $changelog" $web_file

  if [ -s $changelog ]
  then
    echo "setting UNICORN_WORKERS = ${unicorn_workers}"
    rm $changelog
  fi

  echo $data_file memory parameters updated.
}

##
## standard http / https ports must not be occupied
##
check_ports() {
  check_port "80"
  check_port "443"
  echo "Ports 80 and 443 are free for use"
}

##
## check a port to see if it is already in use
##
check_port() {
  local valid=$(netstat -tln | awk '{print $4}' | grep ":${1}\$")

  if [ -n "$valid" ]; then
    echo "Port ${1} appears to already be in use."
    echo
    echo "This will show you what command is using port ${1}"
    lsof -i tcp:${1} -s tcp:listen
    echo
    echo "If you are trying to run Discourse simultaneously with another web"
    echo "server like Apache or nginx, you will need to bind to a different port"
    echo
    echo "See https://meta.discourse.org/t/17247"
    echo
    echo "If you are reconfiguring an already-configured Discourse, use "
    echo
    echo "./launcher stop app"
    echo
    echo "to stop Discourse before you reconfigure it and try again."
    exit 1
  fi
}

##
## read a variable from the config file
##
read_config() {
  config_line=`egrep "^  #?$1:" $web_file`
  read_config_result=`echo $config_line | awk  -F":" '{print $2}'`
  read_config_result=`echo $read_config_result | sed "s/^\([\"']\)\(.*\)\1\$/\2/g"`
}

read_default() {
  config_line=`egrep "^  #?$1:" samples/standalone.yml`
  read_default_result=`echo $config_line | awk  -F":" '{print $2}'`
  read_default_result=`echo $read_config_result | sed "s/^\([\"']\)\(.*\)\1\$/\2/g"`
}

##
## display the config file values to the user
##
display_config() {
  # NOTE: Defaults now come from standalone.yml

  local changelog=/tmp/changelog.$PPID
  read_config "DISCOURSE_SMTP_ADDRESS"
  local smtp_address=$read_config_result
  # NOTE: if there are spaces between emails, this breaks, but a human should be paying attention
  read_config "DISCOURSE_DEVELOPER_EMAILS"
  local developer_emails=$read_config_result
  read_config "DISCOURSE_SMTP_PASSWORD"
  local smtp_password=$read_config_result
  read_config "DISCOURSE_SMTP_PORT"
  local smtp_port=$read_config_result
  read_config "DISCOURSE_SMTP_USER_NAME"
  local smtp_user_name=$read_config_result

  if [ "$smtp_password" = "pa$$word" ]
  then
    smtp_password=""
  fi

  read_config "LETSENCRYPT_ACCOUNT_EMAIL"
  local letsencrypt_account_email=$read_config_result
  
  if [ "$letsencrypt_account_email" = "me@example.com" ]
  then
    letsencrypt_account_email=""
  fi

  read_config "DISCOURSE_HOSTNAME"
  hostname=$read_config_result

  echo ""

  ##
  ## automatically set correct user name based on common mail providers unless it's been set
  ##
  if [ "$smtp_user_name" == "user@example.com" ]
  then
    if [ "$smtp_address" == "smtp.sparkpostmail.com" ]
    then
      smtp_user_name="SMTP_Injection"
    fi
    if [ "$smtp_address" == "smtp.sendgrid.net" ]
    then
      smtp_user_name="apikey"
    fi
    if [ "$smtp_address" == "smtp.mailgun.org" ]
    then
      smtp_user_name="postmaster@$hostname"
    fi
  fi

  if [ ! -z $letsencrypt_account_email ]
  then
    check_IP_match $hostname
  fi

  echo "Hostname      : $hostname"
  echo "Email         : $developer_emails"
  echo "SMTP address  : $smtp_address"
  echo "SMTP port     : $smtp_port"
  echo "SMTP username : $smtp_user_name"

  if [ ! -z $letsencrypt_account_email ]
  then
    echo "Let's Encrypt : $letsencrypt_account_email"
  fi

  echo ""
}

##
## is our config file valid? Does it have the required fields set?
##
validate_config() {
  valid_config="y"

  for x in DISCOURSE_SMTP_ADDRESS DISCOURSE_SMTP_USER_NAME DISCOURSE_SMTP_PASSWORD \
    DISCOURSE_DEVELOPER_EMAILS DISCOURSE_HOSTNAME
  do
    read_config $x
    local result=$read_config_result
    read_default $x
    local default=$read_default_result

    if [ ! -z "$result" ]
    then
      if [[ "$config_line" = *"$default"* ]]
      then
        echo "$x left at incorrect default of $default"
        valid_config="n"
      fi

      config_val=`echo $config_line | awk '{print $2}'`

      if [ -z $config_val ]
      then
        echo "$x was not configured"
        valid_config="n"
      fi
    else
      echo "$x not present"
      valid_config="n"
    fi
  done

  if [ "$valid_config" != "y" ]; then
    echo -e "\nSorry, these $web_file settings aren't valid -- can't continue!"
    echo "If you have unusual requirements, edit $web_file and then: "
    echo "./launcher bootstrap $app_name"
    exit 1
  fi
}

##
## template file names
##

if [ "$1" == "2container" ]
then
  app_name=web_only
  data_name=data
  web_template=samples/web_only.yml
  data_template=samples/data.yml
  web_file=containers/$app_name.yml
  data_file=containers/$data_name.yml
else
  app_name=app
  data_name=app
  web_template=samples/standalone.yml
  data_template=""
  web_file=containers/$app_name.yml
  data_file=containers/$app_name.yml
fi

changelog=/tmp/changelog

##
## Check requirements before creating a copy of a config file we won't edit
##
check_root
check_docker
check_disk_and_memory

if [ -a "$web_file" ]
then
  echo "The configuration file $web_file already exists!"
  echo
  echo ". . . reconfiguring . . ."
  echo
  echo
  DATE=`date +"%Y-%m-%d-%H%M%S"`
  BACKUP=$app_name.yml.$DATE.bak
  echo Saving old file as $BACKUP
  cp $web_file containers/$BACKUP
  echo "Stopping existing container in 5 seconds or Control-C to cancel."
  sleep 5
  ./launcher stop app
  echo
else
  check_ports
  cp -v $web_template $web_file

  if [ "$data_name" == "data" ]
  then
    echo "--------------------------------------------------"
    echo "This two container setup is currently unsupported. Use at your own risk!"
    echo "--------------------------------------------------"
    DISCOURSE_DB_PASSWORD=`date +%s | sha256sum | base64 | head -c 20`

    sed -i -e "s/DISCOURSE_DB_PASSWORD: SOME_SECRET/DISCOURSE_DB_PASSWORD: $DISCOURSE_DB_PASSWORD/w $changelog" $web_file

    if  [ -s $changelog ]
    then
      rm $changelog
    else
      echo "Problem changing DISCOURSE_DB_PASSWORD" in $web_file
    fi

    cp -v $data_template $data_file
    quote=\'
    sed -i -e "s/password ${quote}SOME_SECRET${quote}/password '$DISCOURSE_DB_PASSWORD'/w $changelog" $data_file

    if  [ -s $changelog ]
    then
      rm $changelog
    else
      echo "Problem changing DISCOURSE_DB_PASSWORD" in $data_file
    fi
  fi
fi

scale_ram_and_cpu
display_config
validate_config

##
## if we reach this point without exiting, OK to proceed
## rebuild won't fail if there's nothing to rebuild and does the restart
##
echo "Updates successful. Rebuilding in 5 seconds."
sleep 5 # Just a chance to ^C in case they were too fast on the draw

if [ "$data_name" == "$app_name" ]
then
  echo Building $app_name
  ./launcher rebuild $app_name
else
  echo Building $data_name now . . .
  ./launcher rebuild $data_name
  echo Building $app_name now . . .
  ./launcher rebuild $app_name
fi
