---
title: "Corrected Caddy config for accessing the Nextcloud AIO interface"
date: "2026-11-04 20:35"
category: "Blog"
status: "published"
---

If you run Nextcloud behind Caddy and run into the issue that the hyperlink from your Nextcloud's admin page to its AIO page is missing the port number, here is the fix.
This happens because the documented Caddy configuration snippet for reverse proxying the AIO page is very slightly incomplete (just 4 missing characters).

When Nextcloud and Caddy are configured correctly, Nextcloud AIO is able to detect the URL via which the user connects, and construct the hyperlink from that URL.
This is more than just a convenience; the AIO page has greater access than the regular admin page and is often accessible only on a private network or VPN, with a different IP address and hostname.
Furthermore, the Nextcloud admin page participates in securing the AIO page by adding a token to the AIO hyperlink, which the AIO page verifies before ever even showing a password prompt.
This mechanism is only active while Nextcloud is running, and complements other protections such as the limit on password retries and a five minute attempt timeout.
The broken AIO hyperlink therefore requires the administrator to manually add the port number in their browser's address bar, because accessing the AIO requires both the correct host:port and the token in the URL.

## How do I know if this affects my Nextcloud?

This problem only affects Nextcloud instances installed with the "All-in-One" (AIO) method, running behind Caddy as a reverse proxy, and using a port other than 443 for the AIO page.

Log in to your Nextcloud as an administrative user, click on your profile in the upper right corner, and select "Administration settings".
The top item on the page will be a button labeled "Open Nextcloud AIO Interface ↗".
If this button works for you, and opens a page offering "Nextcloud AIO Login", then there is nothing wrong with your Nextcloud.

If Caddy is misconfigured then you will be taken to the right host but wrong port for your AIO, and your browser may complain that it cannot connect.
If this happens to take you to a port where you are hosting something other than the AIO, then congratulations, you just revealed a (thankfully ephemeral and quite limited) token to that service.
The most common version of this symptom might be that the AIO link takes you to an error page on the Nextcloud, which will happen if you expose Nextcloud and the AIO on the same domain with different port numbers.

## How can I fix it?

Here is a corrected Caddyfile snippet for reverse-proxying the AIO page.
Copy and paste this into your Caddyfile, replacing the previous AIO site block.

```Caddyfile
https://<your-nc-domain>:8443 {
    reverse_proxy https://localhost:8080 {
        header_up Host {hostport}
        transport http {
            tls_insecure_skip_verify
        }
    }
}
```

You must reload Caddy's configuration to apply the config change, such as with `sudo systemctl reload caddy.service`.
Then stop and restart the containers using the AIO to update the `AIO_URL` environment variable in the Nextcloud container.
You can check the current value of `AIO_URL` in the running Nextcloud container using this command:

```bash
sudo docker exec nextcloud-aio-nextcloud printenv AIO_URL
```


For comparison, here's the documented config snippet at the time of publication ([GitHub permalink](https://github.com/nextcloud/all-in-one/blob/81fcda1670fae8d4b9e0eaf6bff18f8ef555cc86/reverse-proxy.md#6-optional-get-a-valid-certificate-for-the-aio-interface)).
The only difference is the `header_up` line.

```Caddyfile
https://<your-nc-domain>:8443 {
    reverse_proxy https://localhost:8080 {
        header_up Host {host}
        transport http {
            tls_insecure_skip_verify
        }
    }
}
```

## How does the fix work?

The updated Caddyfile snippet **includes the port number when copying the host from the original HTTP request header** into the header of the request it makes to the AIO page.

When you click "Start containers" on the AIO page, AIO uses the `Host` header of that request to set the `AIO_URL` environment variable in the Nextcloud container.
AIO relies on Caddy to forward the correct value from the original request, and it does not check `X-Forwarded-Host`.
The hyperlink on the admin page is constructed from the value of `AIO_URL`.

When Caddy reverse proxies an upstream HTTPS site (such as the AIO in this case), it sets `Host` to the host and port used to reach that upstream, and copies the `Host` from the original request to `X-Forwarded-Host`.
The Caddyfile snippet in the documentation does attempt to fix this with the line `header_up Host {host}`, but this drops the downstream port number if one is used.

## How did I find this?

My config was missing the `header_up` line completely, which caused the AIO link to send me to localhost.
I reverse proxy my AIO page only to a domain on a VPN, with a special port number to accommodate other services that are proxied the same way.
Checking the value of `AIO_URL` with the command above made it possible to isolate the issue.

## Software versions

I tested this using Caddy version 2.11.7 and Nextcloud 34.0.5, with Nextcloud AIO version 14.4.3.
Claude Code checked the source code of Caddy, Nextcloud AIO, and Slim-Psr7 at the release tags `v2.11.7`, `v14.4.3`, and `1.8.0` respectively.
Slim-Psr7 1.8.0 is the version AIO 14.4.3 pins in `php/composer.lock`.
