Title: Publishing my banner image generator
Date: 2026-09-12 11:34
Category: Blog
Status: draft

Back in 2021, I wrote a script to create the colorful banner images I use on LinkedIn, GitHub, and Thingiverse.
Today this tool is available as `geometric-banner` on [PyPI](https://pypi.org/project/geometric-banner/).

![A banner generated with geometric-banner]({static}/images/geometric_banner.png "A banner generated with geometric-banner")

I chose the [Viridis](https://bids.github.io/colormap/) color scheme and Gaussian process noise to create an aesthetic similar to that of scientific data visualizations.
The method doesn't use any data, so you can see the resulting images as abstract art.
Or&mdash;if you happened to be considering a Gaussian process model with a Matern kernel, a fixed ν=1.5, and a fixed length scale (which would be an example of simple [Kriging](https://en.wikipedia.org/wiki/Kriging))&mdash;you could generate multiple images as a [prior predictive check](https://mc-stan.org/docs/stan-users-guide/posterior-predictive-checks.html#example-of-prior-predictive-checks).

Eddie Darling made a [nice contribution](https://github.com/JEHoctor/geometric-banner/pull/1) in 2023 that added a [Click](https://click.palletsprojects.com/en/stable/) CLI and the option to use a tessellation of triangles rather than hexagons.
Yesterday I switched from Click to [Typer](https://typer.tiangolo.com/), and made some other cleanup/modernization changes.

You can easily try it out with [uv](https://docs.astral.sh/uv/):

```bash
uvx geometric-banner --help
```

I hope the tool is fun to hack on for anyone interested.
Perhaps we could use AI to add new aesthetics based on other ML techniques?
This should also be a fun repo for traditional coding using the human brain; you can implement any algorithm that inspires you and it does not matter if it's fast or covers every case&mdash;unless you want it to!
PRs welcome.
