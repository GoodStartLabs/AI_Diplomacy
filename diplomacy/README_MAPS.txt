Map File Syntax
***************************

The engine already supports a number of existing map variants, each of which is implemented
by a .map file in the format described here.

***************************
General Directives
***************************

>>> # comment...

Any line that has a pound sign (#) as its first non-whitespace character will be considered
a comment, and ignored. Comments must span a complete line (that is, you may not add a comment
to the end of a non-comment line).

>>> USE[S] fileName...

This line causes another file to be immediately read in. This is used to share map information.
For example, the britain.map file USES the standard.geography file, which contains all the
geography for the standard Diplomacy map.

>>> MAP mapName

This line is identical to USE mapName.map with the additional provision that the graphical
map template (used to generate the actual visual map) will be the one having the mapName
specified. For example, the "fleetRome" map not only USEs the same map data (slightly altered)
as the standard map, but also uses the same graphical map for display (and therefore, the MAP
command is proper for that variant). By contrast, the "britain" and "crowded" maps may USE
(that is, load and then alter) the data from the standard map file, but (due to the additional
SC dots that must be depicted on the map to support these variants), they use different graphical
maps than does the standard game, so the USE command (rather than MAP) is proper for these variants.

***************************
Geographic Directives
***************************

>>> placeName = abbreviation alias...

This type of line specifies all the recognized aliases for a map location. The placeName
is the long form of the map location (the form to appear in results mailings). The abbreviation
is the engine standard abbreviation for the place-name (the form to appear in all orders when
shown to the player on his Web pages). This standard abbreviation must be exactly three
characters long and must both begin and end with an alphabetic or numeric character. Each
alias is a single word (that is, having no embedded spaces) that is to be recognized as
another name for the location in question. If you wish to specify an alias that is more
than a single word in length, you must join the separate words using plus-sign characters (+).
For example, Norwegian Sea = nwg norwegian nrg norwsea norw+sea

If an alias ends with a question-mark (?), it must not contain a plus-sign, and this indicates
that the alias (without the question-mark) is to be considered "ambiguous." Ambiguous aliases
may not be used in games that use the NO_CHECK rule (the ambiguity will be reported to the
player at the time of order-entry). For example, TYR is an ambiguous alias in the standard
game map, since it is commonly used as an alias for both Tyrolia and the Tyrrhenian Sea.

>>> COAST abbreviation [ABUTS [abut...]] -or-
>>> LAND  abbreviation [ABUTS [abut...]] -or-
>>> WATER abbreviation [ABUTS [abut...]] -or-
>>> PORT  abbreviation [ABUTS [abut...]] -or-
>>> SHUT  abbreviation [ABUTS [abut...]] -or-

This type of line specifies the terrain type and adjacencies for the place-name whose
abbreviation is given. The terrain must be either WATER, LAND, COAST, PORT, or SHUT (impassable).
The only difference between PORT and COAST spaces is that fleets located in PORT spaces may convoy
armies as if they were in water.

The adjacency information given on this line will silently supplant (become valid instead of) any
previous such line for the same location. In this way, maps can be changed on the fly, such that
what was a LAND location can become COAST or WATER and/or can obtain different adjacencies.

The abut locations must be the standard abbreviations (the first abbreviation given after
the equals-sign in each placename line).

Specifying Army and Fleet Restrictions
===========================
This directive is case-sensitive. Army and fleet restrictions are specifyied by use of upper- and
lower-case as described below. Everything must be in upper-case except the following:

The abbreviation for any COAST location that a fleet cannot occupy must be listed entirely in
lowercase. For instance, on the standard map, Spain must be listed as spa since fleets may only
occupy either SPA/SC or SPA/NC. Specifying a location using lower-case after the same location
was given earlier using upper-case, or vice-versa, will cause the previous location's terrain type
and adjacencies to be forgotten.

In the list of adjacencies, any location that a fleet could occupy but into which a fleet cannot
move from the location in question must be listed entirely in lowercase. For example, on the standard
map, Tuscany must be listed as tus in the list of locations adjacent to VEN, since a fleet cannot
move directly from Venice to Tuscany.

In the list of adjacencies, any LAND or COAST location to which an army cannot make a direct
(non-convoyed) move from the location in question must be listed with its first character in uppercase
and the remainder in lower-case. This is useful to specify offshore islands, and therefore no example
on the standard map can be given. Consider, however, allowing an army to be convoyed into the
Tyrrhenian Sea (call it Sicily). To implement this, the Tyrrhenian Sea would be given the terrain type
PORT (to allow both fleets and armies to occupy the space and to allow fleets in that space to convoy)
and all land spaces adjacent to the Tyrrhenian Sea would list their adjacency to that space as Tys
(rather than TYS or tys) to indicate than an army may not move directly to the space despite the fact
that movement from a COAST (such as Naples) to an adjacent PORT (the Tyrrhenian) would otherwise be
allowed. Convoyed movement would be allowed, though, so an order such as A Nap-ION-TYS would be perfectly
valid.

Specifying Multi-Coast Spaces
===========================
If an area abuts a multi-coast province, its adjacencies must list only the coasts that are reachable,
and must not list the main space itself (for example, RUM is listed as being adjacent to BUL/EC, but
not to BUL itself).

The line for every coast of a province should appear in the map file before the line for the space
itself.

If the map will undergo terrain changes during play, it is important to note that the fleet-friendly
space listed last is the one on which a unit in that space will be put if a terrain modification
requires it. For example, if a fleet is in Rome when Venice becomes a WATER space, the map file will
need to direct that Rome becomes a multi-coast province by adding entries for ROM/EC, ROM/WC, and rom.
By listing ROM/WC after ROM/EC, the fleet in Rome will be placed on the west (rather than the east) coast.

>>> DROP abbreviation...

This line will remove all data that was given concerning the place(s) with the specified
abbreviation(s), including all adjacency information. That is, all record of the space will be
forgotten, and no space will be left thinking that it is adjacent to the DROPped location. DROPping
a multi-coast space, without designating any particular coast, will also DROP all information for each
of the coasts. That is, DROP SPA, used on the standard map, will remove all information on Spain, Spain
(north coast), and Spain (south coast).

***************************
Political Directives
***************************

>>> powerName [([ownWord][:[abbrev]])] [center...]

This type of line is used to specify a power name, its "ownership word" and single-letter
abbreviation (for instance, England's ownership word would be "English", and abbreviation would be "E")
and all centers that serve as the home centers for the power. If the ownWord is omitted, the powerName
is used for this purpose, and if the abbrev is omitted, the initial letter of the ownWord is used as
the abbreviation.

Any and all leading underscores (_) in a powerName will not be displayed when the power is referred
to in results and on the graphical map. This is useful to cause powers to alphabetize after others
(and thus be displayed in a specific order in the results and on the graphical map).

A plus-sign (+) appearing anywhere in the powerName indicates that the next character in the name
is to be displayed in upper-case. Any plus-sign appearing in the ownWord will be displayed as a space.

If the center is preceded (immediately, with no intervening space) by a dash (-), the center is
removed (if possible) from any pre-existing list of home centers for the power, and added to the list
of unowned supply centers. This allows for locations to lose "home center" status. Factory and partisan
sites may also be removed in this same manner.

Multiple lines for a single powerName may be used to handle long lists of centers.

This type of line sets a "current power" such that all following lines (that specify initial owned
centers and units) will apply to this power (as opposed to any other) until another powerName directive
is encountered.

>>> UNOWNED [center...] -or-
>>> NEUTRAL [center...] -or-
>>> CENTERS [center...]

This line (all three forms are synonymous) is used to list all unowned supply centers. The
UNOWNED power differs from others in that all centers listed as UNOWNED may be listed elsewhere
without error -- they are silently moved to owned status. Additionally, any "current power" is
forgotten by this line. Again, multiple lines may be used to supply a long list of unowned centers.
If you remove a center from the list of UNOWNED centers (using a dash before its name), that location
is no longer a supply center at all. For example, to make Warsaw a non-supply center on the standard
map, you would need to specify the two lines: "RUSSIA -WAR" and "UNOWNED -WAR" in that order.

>>> DUMMY [ALL] -or-
>>> DUMMY [ALL EXCEPT] powerName... -or-
>>> DUMMIES ALL -or-
>>> DUMMIES [ALL EXCEPT] powerName...

This indicates that either the current power, or all powers, or only those specified by powerName,
or again all powers other than those specified, are to be made a DUMMY power in the game. No player
will take the role of such a power. Such a power can be put into civil disorder using the CD_DUMMIES
rule.

>>> UNPLAYED [ALL] -or-
>>> UNPLAYED [ALL EXCEPT] powerName...

This line removes either the current power, all powers, the specified powerName, or on the
contrary all powers that are not specified. At the same time all information that had been
recorded for those powers is removed as well. This directive is useful to create variants for
a smaller number of players on a specific USEd map. If you remove all powers, you should add
some new powers afterwards, because a game will not start with less than two powers.

***************************
Military Directives
***************************

>>> VICTORY centerCount...

Specifies a list of the supply center counts which will determine victory, from the first
game-year forward (the final listed number is repeated for subsequent years). This line is
optional; if omitted, the VICTORY criterion is set (for all game-years) to one supply center
greater than half the number of centers on the map, unless the VICTORY_HOMES rule is used, in
which case the default is based on the number of home centers.

>>> BEGIN season year phaseType

Specifies the initial game phase. This line is optional; if it is omitted, the initial
game phase will be SPRING 1901 MOVEMENT. Only the final BEGIN listed in the map file will
be used. This allows for map files to USE other map files and then override the start phase.

>>> OWNS center...

Specifies the list of centers owned by the "current power" at the beginning of the game.
If not specified, the list of initially owned centers is set to the home centers that were
listed for the "current power."

>>> CENTERS [center...]

Same as OWNS, but forgets about any previous OWNS lines. If no center is given, the power
will start with no centers at all (if not followed by any new OWNS lines that is).

>>> INHABITS center...

Sets the home centers for this power, overwriting any that are given on the power declaration
line, including partisan and factory sites.

>>> HOME(S) [center...]

Same as INHABITS, but forgets about any previous INHABITS lines. If no center is given, the
power will start with no build sites at all (if not followed by any new INHABITS lines that is).

>>> UNITS

This line is optional. If given, all units that have been listed as initial units for the
"current power" are immediately forgotten. This can be used to alter the starting position
of a power from that given in a USEd file.

>>> unit

Specifies a unit that the current power owns at the beginning of the game. The unit will
replace any unit that may have previously been listed as beginning in that same space,

***************************
Behavioral Directives
***************************
>>> RULE[S] rule...

Specifies a rule that will be in effect for all games using this map. For example,
RULE BUILD_ANY would appear in a map file for the Chaos variant, since that variant allows players
to build new units in any unoccupied, owned supply center. If this line occurs outside of a
DIRECTIVE stanza, it will be in effect for all games using this map, regardless of any rules-variant
(payola, etc.) that the game may use. Note that if any rule name is prepended by exclamation point (!),
that rule will be turned off if possible, and this will be done after all other RULEs have been
processed.
