# Ansible with Docker

Setup for using **Ansible** to create droplets in **Digital Ocean** that run **Docker** containers and a MySQL database.

Tested with Ansible 2.8.0.

### 1) Create an account in Digital Ocean (if you don't have already)

### 2) Generate a token in https://cloud.digitalocean.com/account/api/tokens

### 3) Create Firewalls in https://cloud.digitalocean.com/networking/firewalls to allow requests from anywhere to any of the droplets.

#### 3.1) For a more granular (and secure) approach using tags:

```
- Firewall01 (External SSH): [YourIP] -> Port 22 -> (tag) main
- Firewall02 (Internal SSH): (tag) main -> Port 22 -> (tag) host
- Firewall03 (Internet): All IPs -> All Ports -> (tag) web
```

The machine with Ansible (has the `main` tag) will be the only one that can be accessed externally through SSH, and using your IP should remove the threat of brute force attacks.

The other machines (have the `host` tag) can be accessed through SSH from the Ansible machine. Inside the machine with Ansible, run `ssh host@[hostIP]`, assuming the user name in the other machines is `host` (the default in this setup).

The created droplets have the `web` tag, allowing them to be accessed from anywhere in all ports (for a demo, it should be fine, but for production servers a loadbalancer should be included to receive connections from the internet and forward them to the correct containers in the correct ports).

### 4) Create a droplet in Digital Ocean:

```
- Ubuntu 18.04
- US$ 5.00
- User Data: paste the text in /setup/ansible.sh in the textarea
- Tags: main
```

### 5) Connect to the droplet through SSH:

```
- Accept the fingerprint (if asked, type 'yes' and press ENTER)
- SSH password: abc321
```

### 6) Verify that the droplet preparation is finished

```
- Run: tail /var/log/setup.log
- See if the last line printed is: "Setup Finished" (wait while it isn't finished)
```

### 7) Prepare the script to download the repository and run the playbook:

```
$ nano run.sh
[paste the content of the file run.sh in this repository]
Save and exit: Ctrl+X -> y -> ENTER
chmod +x run.sh
```

### 8) Run the script:

```
./run.sh
```

It may give an error the first time, because the Digital Ocean API token is not defined, so define it in `~/env/env.yml`:

```
$ nano ~/env/env.yml
[paste the token of step [2] in the first field `do_token`, then uncomment the `droplet_state` that has the value `present` and comment the one that has the value `deleted` (see step [9] for more information)]
Save and exit: Ctrl+X -> y -> ENTER
$ ./run.sh
```

After running the playbook, you should see the new droplets created in your Digital Ocean dashboard. 

### 9) Alternatives to run ansible:

Instead of running with:

```
$ ./run.sh
```

You can run with:

```
$ cd ~/ansible
$ ansible-playbook main.yml
```

(this won't update the repository with changes, while with `./run.sh` will (good for development), except for the files inside the `env` directory, that are defined only in the 1st run)