// Comments
// -----------------------------
// Order Syntax
// -----------------------------
// *** Recommended syntax **
A LON H
F IRI - MAO
A IRI - MAO VIA
A WAL S F LON
A WAL S F MAO - IRI
F NWG C A NWY - EDI
A IRO R MAO
A IRO D
A LON B
F LIV B

// *** Other possible syntax **
// Hold
A LON H
PAR H

// Move
F IRI - MAO
F IRI - MAO VIA
IRI - MAO
IRI - MAO - XXX - YYY - ZZZ

// Support
A WAL S F LON
WAL S LON
A WAL S LON
F WAL S F MAO - IRI

// Convoy
F NWG C A NWY - EDI
NWG C NWY - EDI

// Retreat (Retreat Phase)
A IRO R MAO
RETREAT IRO - MAO
A IRO D
RETREAT IRO DISBAND

// Build
A LON B
F LIV B
BUILD A LON
BUILD F LIV

// Remove
F LIV D
REMOVE F LIV
DISBAND F LIV

// Waive
WAIVE
