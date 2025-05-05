Title: I switched to Caddy
Date: 2025-05-05 15:19
Category: Blog
Status: draft

In a [previous blog post]({filename}/i-use-uv-to-simplify-certbot-automation.md), I described how I use nginx to serve my blog, and how uv makes it easier to setup Certbot to manage TLS certificates.
I've since switched to [Caddy](https://caddyserver.com/), which manages certificates for me.
I never really had any trouble with my nginx+uv+Certbot setup, but Caddy made it much easier to set up TLS on the content I host on my tailnet.
Tailscale has useful documentation about this [here](https://tailscale.com/blog/caddy).
At one point I had Caddy serving content on all my Tailscale devices, and hoctor.net had nginx and Caddy attached to different interfaces.
It's simpler to use just one tool.
