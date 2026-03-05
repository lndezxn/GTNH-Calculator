# GTNH Calculator — saved workspace
# Saved 1 variable(s)
#
# This file is auto-generated. You can also edit it by hand.
# It will be exec'd in the REPL namespace, so unit names like EU,
# tick, RF etc. are available.

steam_per_water = 160
smelt_per_ingot = 144 * (L / item)

bv_coal = 1600 * bv / item
bv_creosote = 6400 * bv / B

def rc_lpboiler_output(n, h = 1000):
    return 10 * n * (h / 500) * (L/t)

def rc_hpboiler_output(n, h = 1000):
    return 20 * n * (h / 500) * (L/t)

def rc_lpboiler_input(n, h):
    return (n / 16) * ((100 - n)/10 + 0.8 * min(h / 500, 1)) * (bv / t)

def rc_hpboiler_input(n, h):
    return (n / 8) * ((120 - n)/10 + 0.8 * min(h / 500, 1)) * (bv / t)