# makefun-gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Rizal9/makefun-gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Rizal9/makefun-gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A forecaster for Grand Theft Auto VI's launch-day Twitch viewers, hour by hour. One hour into release day it reads the case's hour-1 print and the launch-day shapes of past big launches, and writes five quantiles (5%, 25%, 50%, 75%, 95%) of the concurrent viewers for each of hours 2 to 24.

The model: across past launches, the log-ratio of each later hour to hour 1 is almost linear in log(hour-1 viewers) — a launch that was already huge at hour 1 stays flat, one that was still small surges later. For every hour the program fits that line over peer launches (rolling-midnight launches whose hour 1 was a real launch hour, not the quiet before a later global unlock), smooths the fit across neighbouring hours, and centres its quantiles on the line evaluated at GTA VI's own hour-1 print. The spread blends the fit's empirical residual quantiles with a random-walk spread that widens over the day and with extrapolation distance. Standard library only, no network, deterministic.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=abmjq4f4&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
