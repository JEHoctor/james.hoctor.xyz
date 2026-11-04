---
title: "Corrected Caddy config for accessing the Nextcloud AIO interface"
date: "2026-11-04 14:00"
category: "Blog"
status: "draft"
---

If you run Nextcloud behind Caddy, you might have noticed that the hyperlink from Nextcloud's admin page to its AIO page is broken.
This is because Nextcloud's documentation provides a Caddy configuration snippet for reverse proxying the AIO page that is slightly incorrect.
When Nextcloud and Caddy are configured correctly, Nextcloud is able to detect the URL used to access its AIO page, and construct the hyperlink from that URL.
This is more than just a convenience; the AIO page has greater access than the regular admin page and is usually accessible only on a private network or VPN, with a different IP address and hostname.
The Nextcloud admin page participates in securing the AIO page by adding a token to the AIO hyperlink, which the AIO page verifies before showing a password prompt with limited retries.
The broken AIO hyperlink therefore requires the administrator to manually repair the AIO address each time, because accessing the AIO requires both the correct host and the token in the URL.

## How do I know if this affects my Nextcloud?

This problem only affects Nextcloud instances installed with the "All In One" (AIO) method, and running behind Caddy as a reverse proxy.

Log in to your Nextcloud as an administrative user, click on your profile in the upper right corner, and select "Administration settings."
The top item on the page will be a link to "Open Nextcloud AIO Interface."
If this link works for you, and opens a page offering "Nextcloud AIO Login", hosted on a private network or VPN, then there is nothing wrong with your Nextcloud.

If there is something wrong, then you will be taken to localhost instead (or to whatever host your Caddy server uses to talk to your Nextcloud) and your browser will complain that it cannot connect.
If your config is broken such that it takes you to an address where you happen to be hosting something other than the AIO, then congratulations, you just revealed a (thankfully ephemeral) token to that service.

## How can I fix it?

Here is a corrected Caddyfile snippet for reverse-proxying the AIO page. Copy and paste this into your Caddyfile, replacing the previous AIO directive.

```Caddyfile
https://<your-nc-domain>:8443 {
    reverse_proxy https://localhost:8080 {
        header_up Host {http.request.hostport}
        transport http {
            tls_insecure_skip_verify
        }
    }
}
```


For comparison, here's the documented config snippet at the time of publication ([GitHub permalink](https://github.com/nextcloud/all-in-one/blob/81fcda1670fae8d4b9e0eaf6bff18f8ef555cc86/reverse-proxy.md#6-optional-get-a-valid-certificate-for-the-aio-interface)).

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

The updated Caddyfile snippet **copies the host and port information from the original request header** into the header of the request it makes to the AIO page.

The Nextcloud AIO page reads the `Host` HTTP header, and sets the `AIO_URL` environment variable to the last observed value when it restarts Nextcloud.
It relies on Caddy to forward the correct value from the original request.
The hyperlink on the admin page can then be constructed correctly because `AIO_URL` is set correctly.

When Caddy is reverse proxying an HTTPS request to an HTTPS site using `tls_insecure_skip_verify` (which the snippet does need to use here), the default is to rewrite the `Host` header to the host that Caddy uses to connect to the AIO, dropping the original `Host` header that contains the host used to connect to Caddy.
The Caddyfile snippet in the documentation does attempt to fix this with the line `header_up Host {host}`, but this does not have the desired effect.
Using `http.request.hostport` preserves the host and port of the original request.
It even simplifies the `Host` value to just the host (no port) when the port is the usual 443 port used with HTTPS connections.
