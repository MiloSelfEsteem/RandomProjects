"""
CS2 Lineup Viewer — map calibration data
=========================================
Everything in this file is DATA, not app behavior: per-map named-zone
boxes and schematic fallbacks (MAP_ZONE_LAYOUT, MAP_IMAGE_REGIONS),
precisely-measured individual callout label positions (CALLOUT_POINTS),
and the real-setpos-derived coordinate conversions (MAP_CALIBRATION),
plus the two small matching functions that consume them
(_guess_callout_pins, _setpos_stand_point).

Pulled out of cs2_lineups.py into its own module because this data
alone was over 600 lines — most of the file — and keeping it separate
makes it far easier to find and edit a specific map's calibration
without wading through UI code. Every number in here came from either
directly measuring pixel positions on the actual map images, or real
`setpos` coordinates pulled from cs2util.com / Steam guides and cross-
validated (see the comments throughout, especially above
MAP_CALIBRATION, for the honest accuracy/validation history of each
map — some are solid multi-point fits, a couple are single-fit and
unvalidated, and that's noted explicitly rather than glossed over).

Run this file directly (`python calibration_data.py`) to self-test it —
see run_selftest() at the bottom. cs2_lineups.py imports everything it
needs from here; nothing in this file depends on Tkinter or the network.
"""

import re

# Original, simplified schematic positions (relative 0-1 coordinates) for
# each map's named zones, based on publicly documented callouts (cross-
# checked against cs2flow.com/maps) — not traced from Valve's in-game
# radar art. Matched case-insensitively against whatever area names
# cs2util actually groups lineups under, so a near-miss (e.g. "Cat" vs
# "Catwalk") just falls back to the auto-grid rather than breaking.
# T spawn is implied off the bottom of each layout; sites sit near the
# top, connecting chokepoints in between. Only the 7 current Active
# Duty maps are filled in; anything else renders as a plain grid.
MAP_ZONE_LAYOUT = {
    "nuke": {
        # Confirmed live against cs2util.com/nuke/smoke's own Area filter.
        "outside": (0.12, 0.55),
        "main": (0.55, 0.28),
        "squeaky": (0.80, 0.28),
        "a site": (0.55, 0.08),
        "ramp": (0.40, 0.68),
        "b site": (0.55, 0.90),
    },
    "dust2": {
        # Confirmed live against cs2util.com/dust2/smoke's own Area filter:
        # xbox, A Long, A Short, Middle, B Site, A Site, A Ramp.
        "xbox": (0.22, 0.45),
        "a long": (0.82, 0.55),
        "a short": (0.65, 0.35),
        "middle": (0.42, 0.50),
        "b site": (0.15, 0.20),
        "a site": (0.85, 0.15),
        "a ramp": (0.68, 0.18),
    },
    "mirage": {
        # Confirmed live: A Site, B Site, Window, Connector, B Short, Mid,
        # A Ramp. ("Palace"/"CT Spawn" aren't real cs2util categories here
        # despite being real map callouts — removed.)
        "mid": (0.50, 0.65),
        "connector": (0.72, 0.45),
        "window": (0.55, 0.55),
        "b short": (0.30, 0.35),
        "a ramp": (0.68, 0.25),
        "a site": (0.78, 0.15),
        "b site": (0.20, 0.15),
    },
    "inferno": {
        # Confirmed live: A Site, B Site, Mid, Cart, A Long, Coffins,
        # T Ramp, CT, Banana. ("CT" and "T Ramp" — my first fetch parsed
        # these as one merged token "CTT Ramp" and I missed CT entirely.)
        "banana": (0.25, 0.45),
        "b site": (0.18, 0.15),
        "cart": (0.60, 0.55),
        "a long": (0.75, 0.40),
        "a site": (0.80, 0.15),
        "mid": (0.48, 0.55),
        "coffins": (0.30, 0.30),
        "t ramp": (0.30, 0.60),
        "ct": (0.88, 0.32),
    },
    "overpass": {
        # Confirmed live: A Site, B Site, Mid, Connector, Water, Toilets,
        # Bank, Bins, Monster, Heaven, A Long, T-Step.
        "a site": (0.80, 0.15),
        "connector": (0.55, 0.45),
        "mid": (0.55, 0.55),
        "water": (0.45, 0.55),
        "toilets": (0.65, 0.35),
        "bank": (0.70, 0.20),
        "bins": (0.35, 0.60),
        "monster": (0.25, 0.30),
        "heaven": (0.20, 0.20),
        "a long": (0.85, 0.35),
        "t-step": (0.40, 0.70),
        "b site": (0.20, 0.15),
    },
    "anubis": {
        # Confirmed live: A Site, B Site, Mid, E Box, Heaven, Main, Boat,
        # A Connection, B Connection.
        "mid": (0.50, 0.55),
        "e box": (0.30, 0.40),
        "heaven": (0.75, 0.25),
        "main": (0.60, 0.35),
        "boat": (0.40, 0.65),
        "a connection": (0.68, 0.30),
        "b connection": (0.28, 0.35),
        "a site": (0.80, 0.15),
        "b site": (0.20, 0.12),
    },
    "ancient": {
        # Confirmed live: A Site, B Site, Mid, Ramp, Short, Long, Donut,
        # Heaven. ("Cave"/"CT Spawn" removed — not real categories here.)
        "mid": (0.50, 0.55),
        "ramp": (0.22, 0.35),
        "short": (0.60, 0.40),
        "long": (0.65, 0.55),
        "donut": (0.68, 0.35),
        "heaven": (0.55, 0.20),
        "a site": (0.80, 0.15),
        "b site": (0.20, 0.15),
    },
}


# (MAP_IMG_DIR / the on-disk map_images folder path stays in cs2_lineups.py
# since it's file-path plumbing tied to the app's runtime layout, not
# calibration data.)

# Clickable region boxes (relative x1,y1,x2,y2) calibrated against a real
# map image, for maps where one has been supplied locally. Same area-name
# keys as MAP_ZONE_LAYOUT so both modes match the same cs2util area names.
# Precise point positions (relative x, y) for individual named callouts —
# not the coarse Area categories above, but the actual small labels drawn
# on the image (e.g. "Mid Doors", "B Car", "Xbox"). Used to pin a specific
# lineup's exact spot when its name mentions one of these, rather than
# just highlighting the whole broad Area zone. Coverage starts with
# Dust 2, where every label has been individually measured; other maps
# can be added the same way over time.
CALLOUT_POINTS = {
    "dust2": {
        "sniper's box": (0.063, 0.024), "b plat": (0.099, 0.069),
        "back site": (0.190, 0.037), "window": (0.242, 0.086),
        "double stack": (0.170, 0.092), "scaffolding": (0.272, 0.122),
        "default": (0.190, 0.135), "big box": (0.118, 0.184),
        "fence": (0.046, 0.218), "boost": (0.118, 0.233),
        # "Short Boost" — confirmed as a real distinct lineup name (e.g.
        # "Top Mid Smoke From Short Boost"), a small ledge right next to
        # A Short that CTs jump-boost onto. Same collision risk as "doors"
        # above: without this entry, "boost" (B-site's) would wrongly
        # match. Position estimated adjacent to A Short/A Stairs since no
        # explicit label exists for this small sub-spot on the image.
        "short boost": (0.60, 0.30),
        "b car": (0.170, 0.233), "close": (0.046, 0.300),
        "closet": (0.157, 0.337), "doors": (0.233, 0.220),
        # "A Doors" — a real, distinct callout (confirmed via research: the
        # wide entrance where Long opens into A site, used to block Ts
        # pushing into A from Long). Without this explicit entry, "doors"
        # (B-site's) was silently matching inside "A Doors" via substring
        # search — a real bug, not a tuning issue: a CT-side A-site smoke
        # was showing its pin sitting on B's door. Position is a careful
        # visual estimate (a wall gap matching "wide entrance" is visible
        # here) rather than a precisely labeled dot, since no "A Doors"
        # text label exists on this particular image.
        "a doors": (0.90, 0.35),
        "b boxes": (0.281, 0.245), "ct mid": (0.373, 0.215),
        "truck": (0.432, 0.157), "close mid doors": (0.465, 0.274),
        "ct spawn": (0.569, 0.165), "a plat": (0.711, 0.108),
        "ninja": (0.654, 0.131), "barrels": (0.838, 0.045),
        "goose": (0.783, 0.070), "a ramp": (0.864, 0.108),
        # There are TWO "Default" labels on this map (one per site) — the
        # bare "default" key above kept only the B-side one since it's a
        # duplicate dict key; this recovers the A-side position under its
        # own distinct name so it isn't silently lost.
        "a default": (0.807, 0.147),
        "elevator": (0.757, 0.204), "cross": (0.805, 0.233),
        "a car": (0.923, 0.253), "a long": (0.864, 0.308),
        "long corner": (0.835, 0.388), "a short": (0.618, 0.272),
        "a stairs": (0.580, 0.346), "mid doors": (0.441, 0.371),
        "xbox": (0.465, 0.416), "mid": (0.445, 0.471),
        "lower tunnels": (0.308, 0.346), "upper tunnels": (0.152, 0.449),
        "barrels / palm": (0.484, 0.539), "mid barrels": (0.484, 0.539),
        "palm": (0.484, 0.539), "right side mid": (0.383, 0.567),
        "top mid": (0.461, 0.626), "blue": (0.722, 0.444),
        "long doors": (0.677, 0.547), "side pit": (0.787, 0.539),
        "pit plat": (0.927, 0.539), "pit": (0.863, 0.572),
        "outer long": (0.677, 0.655), "taxi": (0.691, 0.715),
        "outer tunnels": (0.152, 0.633), "t ramp": (0.093, 0.755),
        "t plat / soccer": (0.200, 0.795), "suicide": (0.433, 0.755),
        "t spawn": (0.368, 0.861),
    },
    "mirage": {
        "van": (0.112, 0.065), "b balcony": (0.223, 0.070), "b apps": (0.349, 0.076),
        "kitchen": (0.389, 0.116), "back alley": (0.555, 0.115), "apts / tv": (0.760, 0.054),
        "apts ramp": (0.818, 0.102), "underpass": (0.458, 0.163), "boost": (0.194, 0.170),
        "arches": (0.276, 0.186), "bench": (0.053, 0.163), "safe": (0.141, 0.243),
        "short": (0.369, 0.249), "door": (0.104, 0.336), "window": (0.197, 0.348),
        "ebox": (0.278, 0.330), "ladder": (0.368, 0.308), "market": (0.179, 0.415),
        "checkout": (0.256, 0.415), "shelf": (0.109, 0.449), "side alley": (0.710, 0.259),
        "t spawn": (0.926, 0.307), "vent": (0.368, 0.365), "catwalk": (0.525, 0.384),
        "mid": (0.534, 0.449), "top mid": (0.736, 0.449), "window / sniper": (0.339, 0.466),
        "chair": (0.556, 0.515), "connector": (0.485, 0.585), "flower": (0.252, 0.573),
        "hole": (0.331, 0.533), "jungle": (0.398, 0.652), "stairs": (0.513, 0.632),
        "tetris": (0.607, 0.656), "sandwich": (0.562, 0.712), "t roof": (0.815, 0.661),
        "apex": (0.665, 0.720), "ramp": (0.729, 0.731), "balcony": (0.641, 0.831),
        "pillars": (0.773, 0.824), "ct spawn": (0.222, 0.774), "trash": (0.393, 0.875),
        "triple": (0.505, 0.845), "default": (0.560, 0.845), "ninja": (0.515, 0.938),
        "firebox": (0.574, 0.930), "ticket": (0.416, 0.954),
    },
    "inferno": {
        "garden": (0.504, 0.014), "sandbags": (0.517, 0.070), "church / construction": (0.640, 0.122),
        "dark": (0.401, 0.111), "coffins": (0.536, 0.108), "quad": (0.401, 0.240),
        "fountain": (0.463, 0.238), "ct": (0.579, 0.184), "tree": (0.656, 0.191),
        "bench": (0.716, 0.200), "truck / well": (0.797, 0.223), "2nd": (0.448, 0.288),
        "1st car": (0.486, 0.300), "boost": (0.607, 0.245), "half wall": (0.469, 0.383),
        "ct spawn": (0.888, 0.349), "speedway": (0.729, 0.321), "banana": (0.435, 0.448),
        "logs": (0.362, 0.509), "long corner / cubby": (0.659, 0.506), "arch": (0.764, 0.498),
        "kitchen": (0.893, 0.460), "a long": (0.797, 0.560), "back site": (0.779, 0.628),
        "library": (0.915, 0.575), "moto": (0.901, 0.629), "t spawn": (0.065, 0.656),
        "ledge": (0.286, 0.608), "t ramp": (0.362, 0.620), "mid": (0.522, 0.643),
        "top mid": (0.677, 0.658), "bottom mid": (0.413, 0.668), "living room / kitchen": (0.314, 0.706),
        "close left": (0.776, 0.690), "graveyard": (0.921, 0.717), "boiler": (0.643, 0.700),
        "under / mexico": (0.451, 0.706), "2nd mid": (0.522, 0.785), "patio": (0.683, 0.778),
        "truck": (0.801, 0.781), "balcony": (0.388, 0.781), "a short": (0.735, 0.827),
        "pit": (0.913, 0.861), "bridge": (0.314, 0.823), "window": (0.606, 0.812),
        "long hall": (0.739, 0.903), "t apts": (0.408, 0.904), "back alley": (0.513, 0.909),
        "stairs": (0.643, 0.940),
    },
    "overpass": {
        "bank": (0.382, 0.042), "van": (0.328, 0.137), "trash": (0.480, 0.151),
        "close left": (0.244, 0.193), "heaven": (0.556, 0.232), "truck": (0.462, 0.215),
        "pit": (0.619, 0.281), "ramp": (0.677, 0.259), "barrels": (0.776, 0.259),
        "pillar": (0.752, 0.323), "sewers / canal": (0.850, 0.325), "flowers": (0.417, 0.313),
        "walkway": (0.523, 0.330), "short": (0.354, 0.320), "boost": (0.559, 0.389),
        "bridge": (0.657, 0.371), "monster": (0.850, 0.420), "abc": (0.523, 0.419),
        "door": (0.564, 0.469), "sandbags": (0.756, 0.440), "water": (0.641, 0.480),
        "tracks / dirt": (0.885, 0.498), "short tunnel": (0.747, 0.516), "cafe": (0.184, 0.388),
        "sandwich": (0.421, 0.403), "long": (0.075, 0.440), "long toilets": (0.170, 0.467),
        "toilets": (0.381, 0.467), "mid": (0.343, 0.538), "connector": (0.492, 0.544),
        "tree": (0.054, 0.559), "balloons": (0.243, 0.577), "rock": (0.133, 0.638),
        "fountain": (0.432, 0.675), "lower tunnels": (0.535, 0.617), "ladder / drop": (0.575, 0.676),
        "upper tunnels": (0.697, 0.705), "alley": (0.815, 0.647), "disco": (0.933, 0.676),
        "playground": (0.353, 0.794), "t spawn": (0.647, 0.895),
    },
    "nuke_outside": {
        "ramp": (0.527, 0.061), "big b": (0.520, 0.153), "boost": (0.507, 0.218),
        "rafters": (0.555, 0.274), "trophy": (0.501, 0.322), "heaven": (0.609, 0.283),
        "ct spawn": (0.780, 0.291), "lockers": (0.607, 0.368), "blue": (0.553, 0.402),
        "ct box": (0.706, 0.431), "radio": (0.436, 0.477), "mustang hut": (0.475, 0.465),
        "t spawn": (0.166, 0.552), "squeaky": (0.479, 0.547), "bridge": (0.588, 0.533),
        "silo": (0.462, 0.625), "tetris": (0.528, 0.639), "vent": (0.502, 0.690),
        "back vent": (0.581, 0.702), "main": (0.542, 0.758), "ct red": (0.614, 0.763),
        "t outer": (0.407, 0.746), "outside": (0.593, 0.823), "secret": (0.648, 0.843),
        "garage": (0.706, 0.818), "t red": (0.533, 0.879),
    },
    "nuke_inside": {
        "ramp": (0.520, 0.048), "bottom ramp": (0.518, 0.165), "dark": (0.518, 0.291),
        "window": (0.579, 0.354), "double doors": (0.533, 0.395), "box": (0.570, 0.542),
        "decon": (0.462, 0.591), "silo": (0.507, 0.617), "vents": (0.497, 0.700),
        "back vents": (0.475, 0.758), "tunnels": (0.633, 0.789), "secret": (0.650, 0.852),
    },
    "anubis": {
        "beach": (0.499, 0.123), "ct spawn": (0.420, 0.221), "tunnel": (0.598, 0.252),
        "heaven": (0.705, 0.203), "fountain": (0.855, 0.258), "hell": (0.727, 0.259),
        "box": (0.719, 0.286), "pillar": (0.833, 0.291), "cave": (0.367, 0.321),
        "ct long": (0.286, 0.376), "b conn": (0.509, 0.329), "camera": (0.627, 0.349),
        "temple / palace": (0.461, 0.408), "plat": (0.232, 0.487), "corner": (0.751, 0.345),
        "headshot": (0.715, 0.423), "a main": (0.715, 0.462), "back site": (0.398, 0.468),
        "window": (0.505, 0.479), "outer b": (0.206, 0.560), "obelisk": (0.321, 0.495),
        "connector / ebox": (0.335, 0.550), "water": (0.707, 0.550), "upper / rugs": (0.787, 0.560),
        "door": (0.564, 0.525), "bridge": (0.499, 0.560), "mid": (0.470, 0.638),
        "pool / canals": (0.568, 0.619), "stairs": (0.672, 0.608), "ruins": (0.339, 0.718),
        "alley": (0.624, 0.707), "t spawn": (0.479, 0.922),
    },
    "ancient": {
        "ct spawn": (0.521, 0.104), "temple": (0.275, 0.123), "plat": (0.100, 0.158),
        "xbox": (0.173, 0.228), "triple": (0.301, 0.253), "boost": (0.160, 0.325),
        "alley": (0.673, 0.236), "connector": (0.553, 0.253), "back halls": (0.829, 0.236),
        "window / red": (0.483, 0.332), "top mid": (0.483, 0.401), "short / totem": (0.277, 0.352),
        "a main": (0.109, 0.390), "donut": (0.277, 0.418), "secret": (0.560, 0.464),
        "cave": (0.715, 0.410), "pillar": (0.804, 0.407), "mid": (0.481, 0.530),
        "jaguar": (0.656, 0.514), "ninja": (0.775, 0.486), "ramp": (0.916, 0.486),
        "bottom mid": (0.388, 0.579), "heaven": (0.591, 0.588), "construction": (0.721, 0.601),
        "boost right": (0.883, 0.567), "outer a": (0.192, 0.619), "split / cube": (0.272, 0.661),
        "ruins": (0.868, 0.644), "water": (0.761, 0.796), "t spawn": (0.496, 0.915),
    },
}

# Full affine conversion (6 params, i.e. correcting for rotation/shear
# between the game's world axes and this image's pixel axes — not just
# independent per-axis scaling) from a lineup's exact in-game setpos
# (world x, y) to a relative (0-1) position on this map's image:
#   rel_x = ax*wx + ay*wy + cx
#   rel_y = bx*wx + by*wy + cy
#
# History, told honestly because the middle attempt genuinely failed:
#  - Started with 4 reference points (T Spawn, CT Spawn, Top Mid, Upper
#    Tunnels): ~8px in-sample error, ~70px cross-validated.
#  - Added 3 more points (Pit, Cross, Xbox) all clustered in the one
#    region the first fit was weak in, and refit on all 7 — this made
#    things WORSE (45px in-sample, 91px cross-validated), because the
#    new points were geographically lopsided, not because affine is the
#    wrong model. Used those 3 as manual "snap" overrides instead of
#    trusting the worse refit.
#  - Gathered 4 MORE points (Suicide, Lower Tunnels, Outer Tunnels,
#    T Plat) specifically on the B/left side, which the data had zero
#    coverage of before. Refitting on all 11 — now genuinely balanced
#    across both sides of the map — actually works: ~70px cross-
#    validated, matching the original 4-point fit's accuracy while
#    covering a much larger area. Tested against two alternatives
#    (piecewise nearest-3-point local fits: 178px; nearest-single-point
#    snap only: 158px) and the single global affine beat both.
# This is now the primary model, fit on all 11 points below.
#
# "reference_points" are the actual points the fit was solved from —
# used as a trust radius: a setpos far (in world units) from every one
# of these is extrapolation the fit hasn't been checked against, and
# gets rejected rather than shown with false confidence.
#
# "snap_points" are exact known (world <-> pixel) correspondences that
# override the fitted formula when a setpos is very close to one —
# worth keeping for Pit specifically, whose individual held-out error
# (133px) was notably worse than the fit's average.
MAP_CALIBRATION = {
    "dust2": {
        "ax": 0.0002502962, "ay": 0.0000049012, "cx": 0.515730,
        "bx": 0.0000139581, "by": -0.0002185758, "cy": 0.703176,
        "reference_points": [
            (-332.0, -754.0), (351.0, 2353.0), (148.032, 182.846),
            (-1729.437012, 1064.032349), (914.9368, 762.1490),
            (1004.968750, 2379.968750), (-275.061340, 1345.347046),
            (-491.968750, -228.032410), (-556.032593, 1334.032349),
            (-1332.026245, 491.968231), (-1450.386963, -551.509766),
        ],
        "trust_radius": 500,  # world units
        # (world_x, world_y, known_rel_x, known_rel_y, snap_radius, label)
        "snap_points": [
            (914.94, 762.15, 0.863, 0.572, 150, "Pit"),  # avg of 2 real setpos samples
        ],
    },
    # Mirage: 6 real reference points (T Spawn, CT Spawn, Side Alley,
    # Jungle, Ticket, Market), all cross-checked against real cs2util
    # console commands. In-sample ~28px, leave-one-out cross-validated
    # ~62px on this 753x646 image — comparable accuracy to Dust 2.
    "mirage": {
        "ax": 0.0002372749, "ay": -0.0000176287, "cx": 0.624649,
        "bx": 0.0000340510, "by": -0.0002925321, "cy": 0.257992,
        "reference_points": [
            (1331.9, -97.05), (-2026.395386, -2029.968750),
            (207.428040, 135.970459), (-1119.970093, -1527.968750),
            (-958.425049, -2415.615967), (-1711.968750, -761.032959),
        ],
        "trust_radius": 500,
    },
    # Inferno: only 4 real reference points (CT Spawn, Half Wall, Banana,
    # Boiler) — leave-one-out CV is noisier with this few points (~73px,
    # similar to how Dust 2's original 4-point fit behaved before more
    # points were added). In-sample ~5px on this 774x739 image.
    "inferno": {
        "ax": 0.0002542958, "ay": 0.0000339158, "cx": 0.304834,
        "bx": -0.0000082251, "by": -0.0002162244, "cy": 0.778262,
        "reference_points": [
            (2035.970947, 1914.969238), (423.748749, 1761.960693),
            (290.327515, 1564.969238), (1290.403564, 307.031555),
        ],
        "trust_radius": 500,
    },
    # Overpass: 5 real reference points (Toilets, Water, Alley, Tracks,
    # T Spawn). Worth noting: the first 4-point version of this fit had
    # a genuine numerical instability (a 1456px cross-validation outlier
    # — the 4 points were too geographically clustered/near-collinear).
    # Adding T Spawn (well-separated, at the bottom of the map) fixed it
    # completely: ~24px in-sample, ~63px cross-validated, in line with
    # the other maps.
    "overpass": {
        "ax": 0.0002292758, "ay": -0.0000047174, "cx": 0.945321,
        "bx": -0.0000367715, "by": -0.0001730824, "cy": 0.286131,
        "reference_points": [
            (-2279.468262, -606.113831), (-1616.992309, -720.975688),
            (-555.855286, -2051.304443), (-230.792908, -1138.039429),
            (-1396.600537, -3183.869042),
        ],
        "trust_radius": 500,
    },
    # Nuke outside/upper level: 4 real reference points (T Spawn, Heaven,
    # Trophy, Silo). Noisier than most other maps (~22px in-sample,
    # ~126px cross-validated) but no wild outlier like Overpass's first
    # attempt — same pattern Inferno's 4-point fit showed. Nuke's B-site
    # interior (nuke_inside) doesn't have setpos calibration yet — no
    # real B-site reference data gathered, so it still falls back to
    # name-matching only.
    "nuke_outside": {
        "ax": 0.0002072910, "ay": -0.0000490296, "cx": 0.387576,
        "bx": -0.0000586054, "by": -0.0001992506, "cy": 0.269827,
        "reference_points": [
            (-1206.097494, -1052.129781), (1136.083466, -387.000550),
            (251.968750, -353.560791), (-115.263977, -1753.593140),
        ],
        "trust_radius": 400,
    },
    # Nuke B-site interior — previously had ZERO real setpos data (see the
    # earlier honest gap disclosure). Found via broader search sources
    # (Steam Community guides, not just cs2util) rather than more cs2util
    # searches, which had genuinely turned up nothing after 4 attempts.
    # Only 3 points (Tunnels, Bottom Ramp, "Double Doors" — the latter
    # from a description of hiding "between observation and double doors",
    # so its exact position carries more uncertainty than the other two).
    # 3 points means an exact-fit with NO independent cross-validation
    # possible — unlike every other calibrated map this session, this one
    # hasn't been checked against a held-out point. Trust radius kept
    # deliberately tight (250, vs 400-500 elsewhere) to limit how far an
    # unvalidated fit is allowed to extrapolate.
    "nuke_inside": {
        "ax": 0.0001037531, "ay": -0.0000752676, "cx": 0.445927,
        "bx": 0.0001747447, "by": -0.0003878805, "cy": 0.068671,
        "reference_points": [
            (677.138000, -1552.031250), (764.276978, 95.968750),
            (340.031250, -688.125061),
        ],
        "trust_radius": 250,
    },
    # Anubis: 4 real reference points (T Spawn, CT Spawn, Ruins, Alley).
    # ~12px in-sample, ~67px cross-validated — healthy, no instability.
    "anubis": {
        "ax": 0.0001286429, "ay": -0.0000149594, "cx": 0.512735,
        "bx": -0.0000476989, "by": -0.0001831130, "cy": 0.614517,
        "reference_points": [
            (-563.988496, -1444.477356), (-499.321503, 2310.0),
            (-1267.967529, -312.916748), (837.969604, -763.972412),
        ],
        "trust_radius": 500,
    },
    # Ancient: 4 real reference points (CT Spawn, T Spawn, Ruins, Split).
    # Noisier than most other maps (~25px in-sample, ~132px cross-
    # validated) — same "noisy but not unstable" pattern as Nuke's
    # 4-point fit (no wild outlier like Overpass's first attempt showed).
    "ancient": {
        "ax": 0.0001744628, "ay": -0.0000129618, "cx": 0.617510,
        "bx": -0.0000362584, "by": -0.0002078858, "cy": 0.404349,
        "reference_points": [
            (-396.656372, 1577.343550), (-735.968689, -2135.968750),
            (1255.947144, -1483.968750), (-2143.968750, -1003.968750),
        ],
        "trust_radius": 500,
    },
}


def _setpos_stand_point(map_key, console_cmd):
    """Parse 'setpos X Y Z' from a lineup's console command and convert
    to a relative (rel_x, rel_y) on this map's image. Checks 'snap_points'
    first — exact known (world <-> pixel) correspondences gathered from
    real cs2util lineups — and uses that known pixel directly if the
    setpos is close enough to one. Otherwise falls back to the affine
    MAP_CALIBRATION, gated by trust_radius from the ORIGINAL fit points
    only (see the long comment above MAP_CALIBRATION for why the snap
    points aren't folded into that fit). Returns None if nothing applies
    — with limited reference data, the honest answer is sometimes 'I
    don't know' rather than a confidently-wrong dot."""
    cal = MAP_CALIBRATION.get(map_key)
    if not cal or not console_cmd:
        return None
    m = re.search(r"setpos\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)", console_cmd)
    if not m:
        return None
    wx, wy = float(m.group(1)), float(m.group(2))

    for snap_wx, snap_wy, snap_rx, snap_ry, snap_radius, _label in cal.get("snap_points", []):
        if ((wx - snap_wx) ** 2 + (wy - snap_wy) ** 2) ** 0.5 <= snap_radius:
            return (snap_rx, snap_ry)

    refs = cal.get("reference_points", [])
    radius = cal.get("trust_radius", float("inf"))
    if refs and min(((wx - rx) ** 2 + (wy - ry) ** 2) ** 0.5 for rx, ry in refs) > radius:
        return None
    rx = cal["ax"] * wx + cal["ay"] * wy + cal["cx"]
    ry = cal["bx"] * wx + cal["by"] * wy + cal["cy"]
    if not (0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0):
        return None
    return (rx, ry)

MAP_IMAGE_REGIONS = {
    "dust2": {
        "b site": (0.013, 0.012, 0.327, 0.404),
        "tunnels": (0.026, 0.404, 0.301, 0.685),
        "t spawn": (0.262, 0.851, 0.484, 0.943),
        # Tightened around just the Xbox dot itself instead of a big box
        # that swallowed half of Middle's territory.
        "xbox": (0.435, 0.395, 0.505, 0.455),
        # "Middle" actually covers two separate dot clusters (Mid/Mid Doors
        # up top, Barrels-Palm/Right Side Mid/Top Mid lower down) — using
        # two tight boxes here instead of one big rectangle that used to
        # swallow Xbox and A Short's territory too.
        "middle": [(0.406, 0.349, 0.524, 0.502), (0.353, 0.520, 0.524, 0.655)],
        "mid": [(0.406, 0.349, 0.524, 0.502), (0.353, 0.520, 0.524, 0.655)],
        # Tightened around the A Short / A Stairs dots — expanded up to
        # y=0.25 after cross-checking against CALLOUT_POINTS found the
        # "A Short" label itself (0.618, 0.272) sitting just outside the
        # old boundary (which started at 0.330).
        "a short": (0.543, 0.25, 0.641, 0.441),
        "short": (0.543, 0.25, 0.641, 0.441),
        "catwalk": (0.543, 0.25, 0.641, 0.441),
        "ct spawn": (0.536, 0.184, 0.628, 0.282),
        # A Ramp's own zone was genuinely wrong before — the box stopped
        # at x=0.75, but the "A Ramp" label itself sits at x=0.864, well
        # outside it. Rebuilt to actually contain A Ramp (0.864, 0.108),
        # A Plat (0.711, 0.108), and Ninja (0.654, 0.131) together — this
        # does overlap "A Site" below/right of it, which is expected
        # given the two areas share real map space; the smaller box
        # (this one) correctly takes priority on click since hit-testing
        # sorts smallest-area-first.
        "a ramp": (0.62, 0.06, 0.90, 0.16),
        # Expanded up to y=0.02 after the same cross-check found "Goose"
        # (0.783, 0.070) and "Barrels" (0.838, 0.045) — both part of the
        # A Site cluster — falling above the old y1=0.10 boundary.
        "a site": (0.75, 0.02, 0.97, 0.30),
        # Expanded up to y=0.30 (was 0.343) — the "A Long" label's own
        # dot (0.864, 0.308) was sitting just outside its own box.
        "a long": (0.628, 0.30, 0.968, 0.796),
        "long": (0.628, 0.30, 0.968, 0.796),
    },
    # These only have A Site / B Site calibrated — the radar images you
    # supplied mark those two clearly, but not the finer sub-areas (Mid,
    # Banana, Connector, etc.). Rather than guess where those land on a
    # real image and risk a wrong-looking overlay, any area besides A/B
    # Site for these maps falls back to the grid strip under the image.
    # Calibrated from full labeled callout images (every named zone read
    # directly off the picture), not just A/B Site markers. Confidence is
    # high for anything with a direct label match; a few categories had no
    # exact-name label visible on the image and are best-effort placements
    # from the surrounding layout — flagged in comments below.
    "ancient": {
        "a site": (0.23, 0.20, 0.35, 0.27),   # "Triple" — orange-outlined bombsite marker
        "b site": (0.77, 0.38, 0.88, 0.44),   # "Pillar" — orange-outlined bombsite marker
        "mid": (0.44, 0.49, 0.53, 0.54),
        "ramp": (0.87, 0.46, 0.97, 0.52),
        "short": (0.23, 0.32, 0.33, 0.39),    # "Short / Totem"
        "long": (0.78, 0.20, 0.89, 0.27),     # no exact "Long" label — placed at "Back Halls", lower confidence
        "donut": (0.23, 0.38, 0.33, 0.45),
        "heaven": (0.54, 0.56, 0.64, 0.63),
    },
    "anubis": {
        # CONFIRMED via research: "Default (B): typically behind the
        # Obelisk", "Back Site (B): common post-plant hold" — the
        # Obelisk/Back Site/Window cluster is B Site, not A. Heaven/
        # Fountain/A Main (the Hell/Box/Fountain/Pillar cluster) are
        # confirmed A-side features. These were swapped before — fixed.
        "b site": (0.28, 0.40, 0.56, 0.52),   # "Back Site"/"Window" + orange-outlined "Obelisk"
        "a site": (0.70, 0.20, 0.80, 0.30),   # orange-outlined "Hell"/"Box", near Heaven/Fountain/A Main
        "mid": (0.42, 0.60, 0.52, 0.68),
        "e box": (0.30, 0.51, 0.40, 0.58),    # "Connector / Ebox"
        "heaven": (0.66, 0.16, 0.76, 0.23),
        "main": (0.66, 0.42, 0.79, 0.51),     # "A Main" — re-verified against the real callout point (0.715, 0.462); previous box had drifted into empty space to the right
        "boat": (0.68, 0.51, 0.78, 0.58),      # no exact "Boat" label — moved near Water/Upper (confirmed approach to A), was wrongly near Pool/Canals
        "a connection": (0.63, 0.34, 0.71, 0.40),  # no exact label — placed near "Camera", lower confidence
        "b connection": (0.44, 0.25, 0.52, 0.30),  # "B Conn" — separated from A Connection in BOTH x and y now
    },
    "inferno": {
        "a site": (0.72, 0.55, 0.86, 0.70),   # "Back Site" core plant zone
        "b site": (0.37, 0.01, 0.64, 0.30),   # "Garden"/"Coffins"/"Fountain"/"1st Car" cluster
        "mid": (0.41, 0.61, 0.68, 0.79),
        "cart": (0.44, 0.26, 0.54, 0.34),     # no exact "Cart" label — placed at "1st Car", moderate confidence
        "a long": (0.75, 0.53, 0.85, 0.60),
        "coffins": (0.49, 0.08, 0.59, 0.14),
        "t ramp": (0.32, 0.58, 0.42, 0.66),
        "banana": (0.39, 0.41, 0.49, 0.47),
        "ct": (0.54, 0.19, 0.64, 0.25),       # its own small labeled callout, distinct from CT Spawn
    },
    "mirage": {
        "a site": (0.39, 0.63, 0.82, 0.96),   # "Triple"/"Default"/"Ninja"/"Ticket"/"Ramp"/"Pillars" cluster
        "b site": (0.02, 0.02, 0.60, 0.46),   # "Van"/"B Balcony"/"B Apps"/"Kitchen"/"Market"/"Ebox" cluster
        "mid": (0.34, 0.38, 0.74, 0.52),
        "window": (0.30, 0.43, 0.40, 0.51),   # "Window / Sniper"
        "connector": (0.44, 0.55, 0.55, 0.63),
        "b short": (0.32, 0.21, 0.42, 0.29),  # "Short"
        "a ramp": (0.68, 0.68, 0.78, 0.78),   # "Ramp"
    },
    "overpass": {
        "a site": (0.35, 0.15, 0.50, 0.23),   # orange-outlined bombsite marker near "Trash"/"Truck"
        "b site": (0.80, 0.28, 0.92, 0.36),   # "Pillar"/"Sewers Canal" cluster
        "mid": (0.30, 0.53, 0.40, 0.59),
        "connector": (0.44, 0.54, 0.55, 0.60),
        "water": (0.58, 0.47, 0.70, 0.53),
        "toilets": (0.33, 0.44, 0.45, 0.50),
        "bank": (0.32, 0.00, 0.44, 0.05),
        "bins": (0.47, 0.39, 0.58, 0.45),     # no exact "Bins" label — placed near "ABC", lower confidence
        "monster": (0.78, 0.39, 0.92, 0.45),
        "heaven": (0.49, 0.20, 0.61, 0.26),
        "a long": (0.03, 0.41, 0.22, 0.51),   # no exact "A Long" label — placed at "Long"/"Long Toilets", lower confidence
        "t-step": (0.50, 0.66, 0.73, 0.74),   # no exact "T-Step" label — placed near Upper Tunnels, lower confidence
    },
    # Nuke splits into two real levels — outside/upper (Outside, Main,
    # Squeaky, A Site, Ramp) and inside/lower (B Site). The app switches
    # backgrounds between "nuke_outside.png" and "nuke_inside.png" rather
    # than using one static image for the whole map.
    "nuke_outside": {
        "outside": (0.56, 0.83, 0.62, 0.87),
        "main": (0.52, 0.75, 0.57, 0.79),
        "squeaky": (0.45, 0.54, 0.51, 0.59),
        "a site": (0.51, 0.41, 0.61, 0.56),
        "ramp": (0.51, 0.05, 0.57, 0.10),
    },
    "nuke_inside": {
        "b site": (0.51, 0.28, 0.66, 0.56),
    },
}


def _guess_callout_pins(map_key, lineup_name):
    """Match a lineup's name (e.g. 'Xbox Smoke From Mid Barrels') against
    the known callout labels for this map, returning up to two pins as
    (label, rel_x, rel_y, kind). kind is "land" for the target/landing
    spot named before "from" (or the whole name if there's no "from"),
    and "stand" for the throw origin named after "from" — these are two
    different concepts and get drawn differently. Longer/more specific
    callout names are tried first so 'mid doors' matches before the
    shorter 'mid'.

    Note on accuracy: this is text-matching against the lineup's own
    name, not analysis of the screenshot images themselves — there's no
    reliable way to derive a minimap position from a first-person
    screenshot without depth/camera-calibration data the site doesn't
    provide. The lineup's exact standing spot IS available precisely,
    as the setpos coordinates in the console command, but plotting
    those accurately requires per-map calibration between the game's
    3D coordinates and this specific image's pixels, which hasn't been
    built yet — name-matching is the accurate-but-imperfect option
    that's actually implemented right now."""
    callouts = CALLOUT_POINTS.get(map_key)
    if not callouts:
        return []
    text = lineup_name.lower()
    if " from " in text:
        land_part, stand_part = text.split(" from ", 1)
        parts = [("land", land_part), ("stand", stand_part)]
    else:
        parts = [("land", text)]
    keys_by_len = sorted(callouts.keys(), key=len, reverse=True)

    found, seen = [], set()
    for kind, part in parts:
        for key in keys_by_len:
            if key in seen:
                continue
            # \d* after the key ignores trailing spawn-variant digits
            # ("T Spawn1", "T Spawn2", "CT Spawn3") — there's only one
            # real T Spawn / CT Spawn per map, the number just picks
            # which of several exact spots within it, so they should all
            # resolve to the same landmark rather than fail to match at
            # all (the \b after the base word used to block this, since
            # a digit right after a letter isn't a word boundary).
            if re.search(r"\b" + re.escape(key) + r"\d*\b", part):
                rx, ry = callouts[key]
                found.append((key, rx, ry, kind))
                seen.add(key)
                break
    return found


# ---------------------------------------------------------------- self-test ----
#
# Run directly (`python calibration_data.py`) to check this data for the
# kinds of mistakes that have actually happened during this project —
# not hypothetical ones. Every check here is OBJECTIVE (coordinates being
# in valid range, a fit reproducing its own inputs) rather than a guess
# about which callout "should" belong to which zone — that kind of
# semantic check produced real false alarms during development (e.g.
# flagging Ancient's "Alley" as misplaced when it was actually a wrong
# assumption about grouping, not a real bug), so it's deliberately left
# out of the automated check to avoid crying wolf on future edits. The
# one exception is Dust 2's zone-box grouping, which found 3 real bugs
# this way (A Ramp, A Site, A Main) and has since been hand-verified
# against the real image, so it's trustworthy enough to keep checking.

def _check_box_coords(label, box):
    x1, y1, x2, y2 = box
    ok = 0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0
    if not ok:
        return f"{label}: invalid box coordinates {box}"
    return None


def _check_point_coords(label, point):
    x, y = point
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        return f"{label}: point {point} outside 0-1 range"
    return None


def _check_calibration_self_consistency(map_key, cal, tolerance_px=60):
    """A calibration's own coefficients should reproduce its own reference
    points reasonably well — this won't catch everything (see the honest
    per-map accuracy notes above), but it WILL catch a transcription
    error (a coefficient copied wrong, a reference point pasted from the
    wrong map) which would show up as a large error even on the fit's
    own training data."""
    problems = []
    refs = cal.get("reference_points", [])
    for wx, wy in refs:
        rx = cal["ax"] * wx + cal["ay"] * wy + cal["cx"]
        ry = cal["bx"] * wx + cal["by"] * wy + cal["cy"]
        if not (0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0):
            problems.append(f"{map_key}: reference point ({wx},{wy}) maps to "
                             f"out-of-image position ({rx:.3f},{ry:.3f})")
    return problems


# Dust 2's zone-box groupings, hand-verified against the real image (see
# the module docstring above for why this isn't extended to every map).
_DUST2_EXPECTED_ZONE = {
    "xbox": "xbox",
    "mid doors": "middle", "mid": "middle", "barrels / palm": "middle",
    "mid barrels": "middle", "palm": "middle", "right side mid": "middle",
    "top mid": "middle",
    "a stairs": "a short", "a short": "a short",
    "a plat": "a ramp", "ninja": "a ramp", "a ramp": "a ramp",
    "elevator": "a site", "cross": "a site", "a car": "a site",
    "goose": "a site", "barrels": "a site", "a default": "a site",
    "a long": "a long", "long corner": "a long", "blue": "a long",
    "back site": "b site", "b plat": "b site", "window": "b site",
    "double stack": "b site", "scaffolding": "b site", "default": "b site",
    "big box": "b site", "fence": "b site", "boost": "b site",
    "b car": "b site", "close": "b site", "closet": "b site",
    "doors": "b site", "b boxes": "b site", "sniper's box": "b site",
}


def _point_in_region(px, py, region):
    boxes = region if isinstance(region, list) else [region]
    for x1, y1, x2, y2 in boxes:
        if x1 <= px <= x2 and y1 <= py <= y2:
            return True
    return False


def run_selftest(verbose=True):
    """Returns (passed: bool, problems: list[str])."""
    problems = []

    for map_key, regions in MAP_IMAGE_REGIONS.items():
        for area, region in regions.items():
            boxes = region if isinstance(region, list) else [region]
            for box in boxes:
                err = _check_box_coords(f"{map_key}/{area}", box)
                if err:
                    problems.append(err)

    for map_key, points in CALLOUT_POINTS.items():
        for label, point in points.items():
            err = _check_point_coords(f"{map_key}/{label}", point)
            if err:
                problems.append(err)

    for map_key, cal in MAP_CALIBRATION.items():
        problems.extend(_check_calibration_self_consistency(map_key, cal))

    dust2_callouts = CALLOUT_POINTS.get("dust2", {})
    dust2_regions = MAP_IMAGE_REGIONS.get("dust2", {})
    for label, zone in _DUST2_EXPECTED_ZONE.items():
        if label not in dust2_callouts:
            continue
        px, py = dust2_callouts[label]
        region = dust2_regions.get(zone)
        if region is None or not _point_in_region(px, py, region):
            problems.append(f"dust2: '{label}' expected inside zone '{zone}' "
                             f"but point ({px:.3f},{py:.3f}) falls outside it")

    passed = len(problems) == 0
    if verbose:
        total_boxes = sum(len(v) if isinstance(v, list) else 1
                           for regions in MAP_IMAGE_REGIONS.values() for v in regions.values())
        total_points = sum(len(v) for v in CALLOUT_POINTS.values())
        print(f"Checked {total_boxes} zone boxes across {len(MAP_IMAGE_REGIONS)} maps, "
              f"{total_points} callout points across {len(CALLOUT_POINTS)} maps, "
              f"{len(MAP_CALIBRATION)} setpos calibrations, "
              f"{len(_DUST2_EXPECTED_ZONE)} Dust 2 zone groupings.")
        if passed:
            print("PASS — no problems found.")
        else:
            print(f"FAIL — {len(problems)} problem(s):")
            for p in problems:
                print(f"  - {p}")
    return passed, problems


if __name__ == "__main__":
    import sys
    ok, _ = run_selftest()
    sys.exit(0 if ok else 1)