Title: I switched to Caddy
Date: 2025-05-05 15:19
Category: Blog

In a [previous blog post]({filename}/i-use-uv-to-simplify-certbot-automation.md), I described how I use nginx to serve my blog, and how uv makes it easier to setup Certbot to manage TLS certificates.
I've since switched to [Caddy](https://caddyserver.com/), which manages certificates for me.
I never really had any trouble with my nginx+uv+Certbot setup, but Caddy made it much easier to set up TLS for the content I host on my tailnet.
(I have a PyPI server, some experiments, some admin pages, and a nav page for each node.)
Tailscale has useful documentation about this [here](https://tailscale.com/blog/caddy).
Eventually, I had setup Caddy on all my Tailscale devices.
On `hoctor.xyz`, I had nginx attached to the public interface, and Caddy attached to the Tailscale interface.
It's simpler to use just one tool, so I rewrote my various nginx configs as a Caddyfile, and uninstalled nginx.
