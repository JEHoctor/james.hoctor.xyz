---
title: "How to secure automated rsync transfers with restricted ssh keys"
date: "2025-04-28 14:13"
category: "Blog"
status: "draft"
---

If you use rsync to send files between machines in any sort of automated process, then you should check the security of that setup.
Using rsync over ssh protects the confidentiality and integrity of the transfer, but the ssh credentials also create a security risk: if your automation is compromised then an attacker could use the ssh credentials to gain access to another machine.
You can follow the recipe below to limit the risk by blocking shell access over ssh, restricting what rsync can read and write, and connecting as an unprivileged user.

The system that initiates the file transfer is called the client, and the other system is called the server, regardless of how the transfer is used to send or receive files.
All of these setup steps are performed on the server, where you will need an account with elevated privileges.

# Step 0: Install rrsync

If the server runs Fedora, you will need to install rrsync, even if you already have rsync installed.
On Debian and Ubuntu, rrsync is packaged with rsync.

```bash
sudo dnf install rsync-rrsync
```

# Step 1: Create an unprivileged user

This recipe uses an unprivileged user account to limit the access granted if an ssh connection bypasses the other protections and opens a shell.
I'll use `transfer` as the user name throughout these instructions.
It's also good to add a descriptive comment for the new user.

If you already have a dedicated unprivileged user for file transfers on the server (perhaps because you've followed these instructions before), then you can choose to reuse that user or to create a new one.

If the server runs Debian or Ubuntu, then run the following:

```bash
sudo adduser --disabled-password --shell /usr/bin/dash --comment "for automated file transfers" transfer
```

On a Fedora system, run this instead:

```bash
sudo useradd --shell /bin/sh --comment "for automated file transfers" transfer
```

# Step 2: Create directories for the new user

We're going to restrict the file transfer user to connect with rsync in only one directory.
Let's create that directory.

```bash
sudo -u transfer sh -c "umask 027 && mkdir /home/transfer/files"
```

The new user also needs an .ssh directory and an authorized_keys file.

```bash
sudo -u transfer sh -c "umask 077 && mkdir /home/transfer/.ssh"
sudo -u transfer sh -c "umask 177 && touch /home/transfer/.ssh/authorized_keys"
```

# Step 3: Create a protected directory

This is where we will temporarily store the files needed by the client.
Only the privileged user on the server can access this directory.
You can delete the directory after configuring the client.
Here I'm using the name of the new user as the directory name.

```bash
(umask 077 && mkdir -p ~/transfer)
```

# Step 4: Create an ssh key

If you plan to use multiple keys with this user, for instance to have more fine-grained control over transfer permissions, then set a good comment on the new key.
Note that this command creates a passwordless key with the `-N` flag.

```bash
ssh-keygen -t ed25519 -f ~/transfer/transfer_id_ed25519 -C "automated file transfer key" -N ""
```

# Step 5: Add the new key to authorized_keys

If you need to use this key to read files, then remove or change the `-wo` flag.
You might want to look at the [man page for rrsync](https://download.samba.org/pub/rsync/rrsync.1).
Note that this is where we restrict rsync access to the `/home/transfer/files` directory.
If you want something else, then change it here.

```bash
echo 'command="/usr/bin/rrsync -wo -munge /home/transfer/files",no-agent-forwarding,no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding '"$(cat ~/transfer/transfer_id_ed25519.pub)" | sudo tee -a /home/transfer/.ssh/authorized_keys > /dev/null
```

The public key is not needed anymore.

```bash
rm ~/transfer/transfer_id_ed25519.pub
```

# Step 6: Optional sshd hardening

You can get the ssh daemon to enforce some of the same limits on the transfer user by adding a drop-in sshd config.
This provides overlapping protection that is especially useful if you find yourself adding new keys often.
First, check what the sshd config currently allows for the transfer user.

```bash
sudo sshd -T -C user=transfer | grep -E 'disableforwarding|permittty|authenticationmethods|permituserrc'
# Expect something like:
# permittty yes
# permituserrc yes
# disableforwarding no
# authenticationmethods any
```

Then add the drop-in config file.

```bash
DROP_IN='/etc/ssh/sshd_config.d/10-limit-transfer.conf'
[ -e "$DROP_IN" ] && echo "drop-in already exists" >&2 && false || sudo tee "$DROP_IN" <<'EOF'
Match User transfer
    AuthenticationMethods publickey
    DisableForwarding yes
    PermitTTY no
    PermitUserRC no
EOF
```

Rerun the sshd config check to observe that the drop-in config will have the right effect.

```bash
sudo sshd -T -C user=transfer | grep -E 'disableforwarding|permittty|authenticationmethods|permituserrc'
# Expect something like:
# permittty no
# permituserrc no
# disableforwarding yes
# authenticationmethods publickey
```

Then verify the new sshd config is valid and reload the sshd service to enable it.

```bash
sudo sshd -t && sudo systemctl reload sshd.service
```

# Step 7: Create a known_hosts file

Replace `example.com` with the hostname the client will use to reach the server.

```bash
echo "example.com $(cut -d ' ' -f -2 -- /etc/ssh/ssh_host_ed25519_key.pub)" > ~/transfer/known_hosts
ssh-keygen -Hf ~/transfer/known_hosts
rm ~/transfer/known_hosts.old
```

An alternative is to use `ssh-keyscan`.
I don't like this option as much because it uses a network-enabled command that doesn't use any authentication.
To be safe, it has to be run on the server, and this creates the constraint that the server needs to be able to reach itself with the same hostname the client will use.

```bash
ssh-keyscan -t ed25519 -H example.com | grep -v '^#' > ~/transfer/known_hosts
```

# Automation setup with the new key

After completing the above steps, the new ssh key will be in a protected folder on the server, in this case `~/transfer/`.
You will also need the `known_hosts` file that will be placed in the same folder, and, like any other rsync connection, the username, hostname, and file path for the transfer.
Move these to the client machine, add them to a secrets manager like vault, or to secrets in your git forge for use in automated deployments.
Delete the copy on the server after copying to the client.
If you lose the client copy, delete the corresponding entry in `/home/transfer/.ssh/authorized_keys` and follow the recipe above to generate a new key.

## Automation setup: on the client

This rsync command will copy files to the directory `/home/transfer/files/destination` on the server.
Of course, you'll want to tailor the rsync flags and parameters to your needs.
For example, you might want to use the `--delete` and/or `--checksum` flags for your use case.

```bash
rsync -rvz -e "ssh -i transfer_id_ed25519 -o UserKnownHostsFile=known_hosts" source/ transfer@example.com:destination/
```

## Automation setup: on the server

To allow another user on the server to read or write the files in the transfer directory, you will need to add them to the `transfer` group.
For example, I want the user `caddy` to be in the `transfer` group, so that the Caddy web server can serve the files.

```bash
sudo usermod -aG transfer caddy
```

Then you might need to set the group read and execute bits on the new user's home directory, so that other users can read the files directory within.
This seems to be dependent on the OS defaults for new users.

```bash
chmod 750 /home/transfer
```

If you need another user to write files, you will also need to set the group write bit on the files directory.

```bash
chmod 770 /home/transfer/files
```

# References

The first reference, *Restrict SSH access to only allow rsync* by Michael Boelen, covers the same topic and was a big inspiration for these instructions.
However, because I do a few things differently, I wrote my own description of the process.
Over the past year, I've performed this setup on four different machines, and I referenced my own instructions each time.

If you do decide to use Michael Boelen's recipe, then be careful when copying the `authorized_keys` line from his example.
Due to a formatting error, the quote characters are left and right double quotation marks (unicode U+201C and U+201D).
This will confuse the ssh daemon when it reads the file; it's expecting the ascii-compatible quotation mark character (U+0022).

The fourth reference is an example of a common automated file transfer that can be secured by restricting ssh access.

 1. [Restrict SSH access to only allow rsync](https://linux-audit.com/ssh/restrict-ssh-access-to-only-allow-rsync) by Michael Boelen
 2. [Manual page for rrsync](https://download.samba.org/pub/rsync/rrsync.1)
 3. [Debian manual page for adduser](https://manpages.debian.org/bookworm/adduser/adduser.8.en.html)
 4. [Deploying to a server via SSH and Rsync in a Github Action](https://dev.to/zellwk/deploying-to-a-server-via-ssh-and-rsync-in-a-github-action-2acd) by Zell Liew
