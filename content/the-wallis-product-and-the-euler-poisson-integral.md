Title: The Wallis Product and the Euler-Poisson integral
Date: 2025-04-14 13:29
Category: Blog
Tags: Math

Years ago I was experimenting with the Euler-Poisson integral in $n$ dimensions when I derived an infinite product for $\pi$ known as the Wallis product.

$$\pi = 2\prod\limits_{i=1}^{\infty}\frac{(2i)^2}{(2i-1)(2i+1)}$$

I was only expecting to calculate the area of $n$-spheres, so I was delighted to find this!
This formula was first published in 1656 by John Wallis.
I'll show the standard Euler-Poisson integral, the way I used it to derive areas and volumes of spheres and balls in arbitrary dimensions, and finally how I derived the Wallis product.
Unfortunately I lost my original derivation, so this is my best reconstruction of my process.

I recently revisited my derivation and found it contained an interesting way to derive the areas of $n$-spheres.
The rest of my derivation of the Wallis product was standard, but I'll show that too.

First, some terminology.
A closed ball is the set of points whose distance from a center point is less than or equal to a fixed radius.
A closed unit ball is a closed ball with radius one, and in $n$ dimensions its volume is denoted $V_n$.

A sphere is the boundary of a ball, i.e. the points at a distance strictly equal to the radius.
A sphere in $n$ dimensions is an $(n-1)$-dimensional surface, and the area of a unit sphere in $n$ dimensions is denoted $S_{n-1}$.
For example, the area of a unit sphere in three dimensions is $S_2=4\pi$.
This convention is better than using the dimension of the embedding space as the subscript because it makes it easy to know when $S_{n-1}$ is defined: the subscript is the dimension of the surface and must therefore be 0 or more for the surface to be measurable.
So $S_1$ is $2\pi$ (the circumference of a unit circle), $S_0$ is 2 (the number of endpoints of an interval), but $S_{-1}$ doesn't make any sense.

# The Euler-Poisson integral

The Euler-Poisson integral in one dimension is $\int_{-\infty}^{\infty}e^{-x^2}dx$.
This is also called the Gaussian integral, and the integrand is the Gaussian function, $e^{-x^2}$.
Poisson computed this integral by squaring it, and noting that this is equivalent to the integral of a Gaussian function in two dimensions.

$$\left(\int\limits_{-\infty}^{\infty}e^{-x^2}dx\right)^2 = \int\limits_{-\infty}^{\infty}e^{-x^2}dx\int\limits_{-\infty}^{\infty}e^{-y^2}dy = \int\limits_{-\infty}^{\infty}\int\limits_{-\infty}^{\infty}e^{-x^2-y^2}dxdy$$

Now convert to polar coordinates.

$$\int\limits_{-\infty}^{\infty}\int\limits_{-\infty}^{\infty}e^{-x^2-y^2}dxdy = \int\limits_{0}^{2\pi}\int\limits_{0}^{\infty}e^{-r^2}r\,drd\theta = \int\limits_{0}^{2\pi}d\theta\int\limits_{0}^{\infty}re^{-r^2}dr = 2\pi\int\limits_{0}^{\infty}re^{-r^2}dr$$

The integral can be solved by inspection.

\begin{align*}
\frac{d}{dr}e^{-r^2} &=  e^{-r^2}(-2r) \\
\left[e^{-r^2}\right]_{0}^{\infty} &= -2\int\limits_{0}^{\infty}re^{-r^2}dr \\
-(e^{-\infty^2} - e^{-0^2})\pi &= 2\pi\int\limits_{0}^{\infty}re^{-r^2}dr \\
\pi &= 2\pi\int\limits_{0}^{\infty}re^{-r^2}dr
\end{align*}

Then we can take the square root of both sides, noting that the integral of a positive function is positive.

\begin{align*}
\left(\int\limits_{-\infty}^{\infty}e^{-x^2}dx\right)^2 &= 2\pi\int\limits_{0}^{\infty}re^{-r^2}dr = \pi\\
\int\limits_{-\infty}^{\infty}e^{-x^2}dx &= \sqrt{\pi}
\end{align*}

# The Euler-Poisson integral in higher dimensions

The main idea of the derivation is already present in Poisson's computation above.
By raising the Euler-Poisson integral to the $n$th power, we get an integral under an $n$-dimensional Gaussian, and this can be converted to a radial coordinate system using spherical shells.

$$\pi^{n/2} = \left(\int\limits_{-\infty}^{\infty}e^{-x^2}dx\right)^n = \int_{\mathbb{R}^n}e^{-||\vec{x}||_2^2}|d\vec{x}| = \int\limits_{0}^{\infty}S_{n-1}r^{n-1}e^{-r^2}dr = S_{n-1}\int\limits_{0}^{\infty}r^{n-1}e^{-r^2}dr$$

The remaining integral is $\int_{0}^{\infty}r^{n-1}e^{-r^2}dr$, and we _could_ use $u$-substitution to express it as a gamma function.
Instead, we're going to call it $J_{n-1}$ and solve it with a recurrence relation.

\begin{align*}
J_n &\equiv \int\limits_{0}^{\infty}r^n e^{-r^2}dr = \int\limits_0^{\infty}(r^{n-1})(-\frac{1}{2})(-2re^{-r^2})dr \\
&= -\frac{1}{2}\left([(r^{n-1})(e^{-r^2})]|_0^{\infty} - \int\limits_0^{\infty}(n-1)r^{n-2}e^{-r^2}dr\right) & \text{(integration by parts)}\\
&= \frac{1}{2}(n-1)\int\limits_0^{\infty}r^{n-2}e^{-r^2}dr = \frac{1}{2}(n-1)J_{n-2} \\
J_0 &= \int\limits_0^{\infty}e^{-r^2}dr = \frac{1}{2}\int\limits_{-\infty}^{\infty}e^{-r^2}dr = \frac{1}{2}\sqrt{\pi} \\
J_1 &= \int\limits_0^{\infty}re^{-r^2}dr = \frac{1}{2}
\end{align*}

With the recurrence and the base cases, we can calculate:

\begin{align*}
J_{2n} &= \frac{1}{2}\sqrt{\pi}\prod\limits_{i=1}^n \frac{1}{2}(2i-1) \\
J_{2n+1} &= \frac{1}{2}\prod\limits_{i=1}^{n}\frac{1}{2}(2i) = \frac{1}{2}n!
\end{align*}

Now we can solve for $S_{2n}$.

\begin{align*}
\pi^{n/2} &= S_{n-1}J_{n-1} \\
\pi^{n+1/2} &= S_{2n}J_{2n} \\
S_{2n} &= \pi^{n+1/2}\frac{2}{\sqrt{\pi}}\prod\limits_{i=1}^{n}\frac{2}{2i-1} = 2\pi^n\prod\limits_{i=1}^{n}\frac{2}{2i-1}
\end{align*}

And similarly for $S_{2n+1}$.

\begin{align*}
\pi^{n/2} &= S_{n-1}J_{n-1} \\
\pi^{n+1} &= S_{2n+1}J_{2n+1} \\
S_{2n+1} &= \frac{2\pi^{n+1}}{n!}
\end{align*}

Let's tabulate a few values to check that these formulas give us the familiar surface area values.

| $n$   | 0 | 1      | 2      | 3        | 4                  |
| ----- | - | ------ | ------ | -------- | ------------------ |
| $S_n$ | 2 | $2\pi$ | $4\pi$ | $2\pi^2$ | $\frac{8}{3}\pi^2$ |

You can recognize the constants from the familiar formulas $2\pi r$ and $4\pi r^2$, and check the other values with a reference.

# Aside: a simpler way to get area and volume formulas

There's an easier way to derive the surface areas of spheres and the volumes of balls using a pair of recurrence relations.
The first recurrence uses the fact that the area of a sphere is the derivative of the volume of a ball of the same radius with respect to that radius.

\begin{align*}
S_{n-1} &= \left. \frac{d}{dr} \left( V_n r^n \right) \right|_{r = 1} = V_n nr^{n-1}|_{r=1} = nV_n \\
V_n &= \frac{1}{n}S_{n-1}
\end{align*}

The second recurrence comes from the appearance of the Wallis integrals in direct recurrences for $S_n$ and $V_n$.
Wikipedia defines them a bit differently, but for our purposes the Wallis integrals are defined as below.

$$I_n \equiv \int\limits_{0}^{\pi}\sin^n \theta\,d\theta$$

Direct recurrences for $S_n$ and $V_n$ can be derived by imagining an axis through a ball or sphere and integrating with respect to the angle formed with the axis.

\begin{align*}
S_n &= \int\limits_{0}^{\pi}S_{n-1}\sin^{n-1}\theta\,d\theta = S_{n-1}I_{n-1} \\
V_n &= \int\limits_{0}^{\pi}V_{n-1}\sin^{n-1}\theta\,\frac{d}{d\theta}(-\cos\theta)\,d\theta = V_{n-1}\int\limits_{0}^{\pi}\sin^{n-1}\theta\,\sin\theta\,d\theta = V_{n-1}I_n
\end{align*}

We can combine these and find that the ratio $S_n/V_{n-1}$ is a constant, which gives the second recurrence.

\begin{align*}
\frac{S_n}{V_{n-1}} &= \frac{S_{n-1}I_{n-1}}{V_{n-2}I_{n-1}} = \frac{S_{n-1}}{V_{n-2}} = \frac{S_1}{V_0} = 2\pi \\
S_n &= 2\pi V_{n-1}
\end{align*}

# The Wallis product

So how does the Wallis product appear out of this?
I don't have my original notes from the first time I derived this, but I think I must have been trying to solve the Wallis integrals

\begin{align*}
I_n &= \int\limits_{0}^{\pi}\sin^{n-2}\theta\,(1-\cos^{2}\theta)d\theta \\
&= \int\limits_{0}^{\pi} \sin^{n-2}\theta\,d\theta - \int\limits_{0}^{\pi}\sin^{n-2}\cos^{2}\theta\,d\theta \\
&= I_{n-2} - \int\limits_{0}^{\pi}\left(\sin^{n-2}\theta\cos\theta\right)\cos\theta\,d\theta \\
&= I_{n-2} -\left.\left[\frac{1}{n-1}\sin^{n-1}\theta\cos\theta\right]\right|_{0}^{\pi} + \int\limits_{0}^{\pi}\frac{1}{n-1}\sin^{n-1}\theta(-\sin\theta)d\theta \\
&= I_{n-2} - \frac{1}{n-1}\int\limits_{0}{\pi}\sin^{n}\theta\,d\theta \\
&= I_{n-2} - \frac{1}{n-1}I_n \\
I_n &= \frac{n-1}{n}I_{n-2}
\end{align*}

Now let's calculate the base cases for the Wallis integrals.

\begin{align*}
I_0 &= \int\limits_{\theta=0}^{\pi}d\theta = \pi \\
I_1 &= \int\limits_{0}^{\pi}\sin\theta\,d\theta = \left.\left[-\cos\theta\right]\right|_{0}^{\pi} = \cos 0-\cos\pi = 2
\end{align*}

Now the odd and even Wallis integrals can get separate formulas.

\begin{align*}
I_{2n} &= \pi\prod\limits_{i=1}^{n}\frac{2i-1}{2i} \\
I_{2n+1} &= 2\prod\limits_{i=1}^{n}\frac{2i}{2i+1}
\end{align*}

Now it's immediately tempting to combine these formulas and solve for $\pi$, by approximating $I_{2n}$ as $I_{2n+1}$.
However, to do this we need show that the ratio of successive Wallis integrals approaches one, and luckily we already have his result for the ratio of Wallis integrals $I_n$ and $I_{n-2}$.
Because $\sin^n\theta$ is less than $\sin^{n-1}\theta$ everywhere on the interval $[0,\pi]$, the sequence of Wallis integrals is decreasing, and we can use the ratio $I_n/I_{n-2}$ to bound the ratio $I_n/I_{n-1}$ as desired.

\begin{align*}
\end{align*}

# References

 1. [https://en.wikipedia.org/wiki/N-sphere](https://en.wikipedia.org/wiki/N-sphere)
 2. [https://en.wikipedia.org/wiki/Gaussian_integral](https://en.wikipedia.org/wiki/Gaussian_integral)
 3. [https://en.wikipedia.org/wiki/Wallis_product](https://en.wikipedia.org/wiki/Wallis_product)
 4. [https://en.wikipedia.org/wiki/Wallis%27_integrals](https://en.wikipedia.org/wiki/Wallis%27_integrals)
 5. [https://en.wikipedia.org/wiki/Volume_of_an_n-ball](https://en.wikipedia.org/wiki/Volume_of_an_n-ball)
