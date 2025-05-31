Title: I use uv to simplify Certbot automation
Date: 2025-01-25 00:44
Category: Blog
Status: published

The VPS hosting this blog is configured to use nginx with a certificate from Let's Encrypt.
I chose Certbot to automate certificate renewal.
The official setup instructions from EFF for Certbot with nginx and pip are [here](https://certbot.eff.org/instructions?ws=nginx&os=pip), but the recommended pip/venv workflow seems inconvenient now that I've started working with [uv](https://docs.astral.sh/uv/).

I'll show you how I simplified Certbot automation using uv, and compare the ten steps in the official instructions to my own steps, noting which steps are easier with uv, and which are easier with pip/venv.
But first, if you're already familiar with uv and Certbot, and you're just looking for the crontab line to make them work together, here it is:

```
0 0,12	* * *	root	/root/.local/bin/uv self update && /usr/bin/python3 -c 'import random; import time; time.sleep(random.random() * 3600)' && /root/.local/bin/uvx --with='certbot-nginx' --refresh certbot renew -q
```

_Update 2025-01-30: After I set this up, I discovered [Caddy](https://caddyserver.com/), an HTTPS server and reverse proxy that automatically handles TLS certificate procurement and renewal.
I'm still using nginx+uv as described here, but if it breaks I plan to switch to Caddy._

_Update 2025-05-05: Read my [new post]({filename}/i-switched-to-caddy.md) about why I switched to Caddy._

# Step by step instructions and comparison

## Step 1: SSH into the server

It is still required to be able to SSH into your server as a privileged user.

## Step 2: Install system dependencies

It is necessary to install uv for the root user, because the cron job that refreshes the certs will run as root.
This is as easy as [running the install script](https://docs.astral.sh/uv/getting-started/installation/) as root.
So, uv requires this one extra setup command, and requires two more if you want to enable uv shell completion for the root user.
Perhaps the biggest downside to the uv approach is that you might just not want this additional tool on your system.

As for the other system dependencies (described in the official instructions), it is not required to install the `python3-venv` package on Debian and Ubuntu, but python3 and Augeas are still required.

## Step 3: Remove certbot-auto and any Certbot OS packages

This step is unnecessary with uv because uv does not have the Certbot versioning issue that the official instructions face.

The official instructions put the command `certbot` on root's `$PATH`, and it's important that only one `certbot` is on the path to guarantee that the same `certbot` being run is the one getting regular updates.
Therefore, any other install of Certbot that might be on the path needs to be removed.

## Steps 4 through 6: Installing Certbot in a venv and putting it on the path

These steps are unnecessary when using uv, eliminating four setup commands.

## Step 7: Get and install your certificates

This step is essentially the same. We just run:

```
uvx --with='certbot-nginx' certbot --nginx
```

Maybe you will run into issues with this if using sudo instead of a root shell.
If so, you could try `sudo su`.

(Note that step 7 has an alternate version in the official instructions that I haven't tested. I'm guessing it would work as expected -- just add "certonly" to the command.)

## Step 8: Set up automatic renewal

Run this command to add the uv-based cron job to the crontab:

```
echo "0 0,12	* * *	root	/root/.local/bin/uv self update && /usr/bin/python3 -c 'import random; import time; time.sleep(random.random() * 3600)' && /root/.local/bin/uvx --with='certbot-nginx' --refresh certbot renew -q" | sudo tee -a /etc/crontab > /dev/null
```

Here's what my cron job runs:

```
/root/.local/bin/uv self update
/usr/bin/python3 -c 'import random; import time; time.sleep(random.random() * 3600)'
/root/.local/bin/uvx --with='certbot-nginx' --refresh certbot renew -q
```

And for comparison, here are the commands in the official cron job:

```
/opt/certbot/bin/python -c 'import random; import time; time.sleep(random.random() * 3600)'
sudo certbot renew -q
```

My first command updates uv itself.
The original instructions don't have an equivalent command.

The next command uses Python to wait a random amount of time up to one hour.
The Python code is the same in both versions, but the official version is careful to use the Python interpreter from the Certbot installation.
I don't think this matters at all, so I've chosen to rely on whatever version of Python 3 is installed.
This is typically going to end up being the exact same interpreter, since the official instructions use system Python to create the Certbot venv.

My final command uses `uvx` (a tool packaged with uv) to run "certbot renew -q" in a temporary venv. The "--with='certbot-nginx'" flag ensures that this venv includes the `certbot-nginx` package. The venv will include the `certbot` package because uv infers this dependency from the command "certbot renew -q". The "--refresh" command ensures that uv checks for a new version of Certbot on PyPI before creating the venv.

## Step 9: Confirm that Certbot worked

Visit your site and confirm that https is enabled.

## Step 10: [Monthly] Upgrade certbot

This is my favorite part.
Using uv eliminates the need to update Certbot each month. The official instructions install Certbot in a venv hidden away under `/opt`, and you would need to either remember this each month, or record the update command in your notes.
Instead, uv uses ephemeral virtual environments, and it guarantees that Certbot will be up-to-date each time it runs.

# Conclusion

You might be thinking that this approach will be slow and inefficient because it builds Python virtual environments.
Actually, uv makes it fast and efficient to create venvs, which is why it provides the `uvx` command for single use venvs.
Building virtual environments with pip and venv is pretty slow.

We could save some network bandwidth by removing the "--refresh" flag for uvx in the cron job, but I'm not sure how to keep uv's package cache reasonably up-to-date without it.

I mainly find using uv is superior because it eliminates a monthly manual update.
It also reduces the number of setup commands, but this is just an extra benefit to me.
If this setup breaks my server in some way, I will post an update to this blog post.
