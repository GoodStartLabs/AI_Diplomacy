#!/usr/bin/env bash
python svg_to_react.py --input src/diplomacy/maps/svg/standard.svg --output src/gui/maps/standard/ --name SvgStandard
python svg_to_react.py --input src/diplomacy/maps/svg/ancmed.svg --output src/gui/maps/ancmed/ --name SvgAncMed
python svg_to_react.py --input src/diplomacy/maps/svg/modern.svg --output src/gui/maps/modern/ --name SvgModern
python svg_to_react.py --input src/diplomacy/maps/svg/pure.svg --output src/gui/maps/pure/ --name SvgPure
