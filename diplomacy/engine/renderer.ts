// diplomacy/engine/renderer.ts

import * as fs from 'fs';
import * as path from 'path';
import { DOMParser, XMLSerializer } from '@xmldom/xmldom';
import { DiplomacyGame } from './game';
import { DiplomacyMap } from './map'; // Assuming DiplomacyMap might be needed directly or via game.map
// import { ParsedOrder } from './interfaces'; // If rendering parsed orders directly

// Constants
const LAYER_ORDER = 'OrderLayer';
const LAYER_UNIT = 'UnitLayer';
const LAYER_DISL = 'DislodgedUnitLayer';
const ARMY = 'Army';
const FLEET = 'Fleet';

// Placeholder for settings if not imported from a central place
const settings = {
    PACKAGE_DIR: path.join(__dirname, '../../..'), // Adjust path as necessary to reach project root
};

// Helper to get attribute value, similar to Python's _attr
function getAttribute(node: Element, attrName: string, namespaceURI?: string | null): string | null {
    if (namespaceURI) {
        const attr = node.getAttributeNS(namespaceURI, attrName);
        return attr;
    }
    const attrItem = node.attributes.getNamedItem(attrName);
    return attrItem ? attrItem.value : null;
}

interface RendererMetadata {
    color: Record<string, string>; // powerName -> colorString
    symbol_size: Record<string, [string, string]>; // symbolName -> [height, width]
    orders: Record<string, any>; // Placeholder, structure depends on jdipNS:ORDERDRAWING specifics
    coord: Record<string, { // provinceName (uppercase, e.g. PAR, MAR/SC)
        unit?: [string, string]; // [x, y]
        disl?: [string, string]; // [x, y]
    }>;
}

export class Renderer {
    private game: DiplomacyGame;
    private metadata: RendererMetadata;
    private xml_map: string | null = null; // Store as string, parse when needed

    constructor(game: DiplomacyGame, svg_path_override?: string) {
        this.game = game;
        this.metadata = {
            color: {},
            symbol_size: {},
            orders: {}, // To be defined by _load_metadata
            coord: {}   // To be defined by _load_metadata
        };

        let svg_path = svg_path_override;
        if (!svg_path) {
            // Default SVG path logic (assuming game.map.name and game.map.root_map are available)
            const map_name = this.game.map_name || 'standard'; // Use game.map_name
            const root_map = this.game.map.root_map || map_name.split('.')[0]; // Ensure map.root_map exists

            for (const file_name of [`${map_name}.svg`, `${root_map}.svg`]) {
                const potential_path = path.join(settings.PACKAGE_DIR, 'maps', 'svg', file_name);
                if (fs.existsSync(potential_path)) {
                    svg_path = potential_path;
                    break;
                }
            }
        }

        if (svg_path && fs.existsSync(svg_path)) {
            this.xml_map = fs.readFileSync(svg_path, 'utf-8');
            this._load_metadata();
        } else {
            console.error(`SVG map file not found at path: ${svg_path} or default paths.`);
            this.xml_map = null; // Ensure xml_map is null if not loaded
        }
    }

    private _load_metadata(): void {
        if (!this.xml_map) {
            console.warn("Cannot load metadata: xml_map is null.");
            return;
        }

        const parser = new DOMParser();
        // Use "text/xml" for parsing if "image/svg+xml" causes issues with custom namespaces
        const doc = parser.parseFromString(this.xml_map, "text/xml");
        const serializer = new XMLSerializer();

        // Define the jdipNS namespace URI if it's defined in the SVG.
        // For now, assume no explicit URI and use wildcard or local name matching.
        const jdipNS = null; // Or the actual namespace URI string

        // Power Colors
        const orderDrawingElements = doc.getElementsByTagNameNS(jdipNS || "*", 'ORDERDRAWING');
        if (orderDrawingElements.length > 0) {
            const powerColorsElements = orderDrawingElements[0].getElementsByTagNameNS(jdipNS || "*", 'POWERCOLORS');
            if (powerColorsElements.length > 0) {
                const powerColorNodes = powerColorsElements[0].getElementsByTagNameNS(jdipNS || "*", 'POWERCOLOR');
                for (let i = 0; i < powerColorNodes.length; i++) {
                    const node = powerColorNodes[i] as Element;
                    const power = getAttribute(node, 'power');
                    const color = getAttribute(node, 'color');
                    if (power && color) {
                        this.metadata.color[power.toUpperCase()] = color;
                    }
                }
            }
            // Symbol Size
            const symbolSizeNodes = orderDrawingElements[0].getElementsByTagNameNS(jdipNS || "*", 'SYMBOLSIZE');
            for (let i = 0; i < symbolSizeNodes.length; i++) {
                const node = symbolSizeNodes[i] as Element;
                const name = getAttribute(node, 'name');
                const height = getAttribute(node, 'height');
                const width = getAttribute(node, 'width');
                if (name && height && width) {
                    this.metadata.symbol_size[name] = [height, width];
                }
            }
        }

        // Province Coordinates
        const provinceDataElements = doc.getElementsByTagNameNS(jdipNS || "*", 'PROVINCE_DATA');
        if (provinceDataElements.length > 0) {
            const provinceNodes = provinceDataElements[0].getElementsByTagNameNS(jdipNS || "*", 'PROVINCE');
            for (let i = 0; i < provinceNodes.length; i++) {
                const node = provinceNodes[i] as Element;
                const provinceNameAttr = getAttribute(node, 'name');
                if (provinceNameAttr) {
                    const provinceKey = provinceNameAttr.toUpperCase().replace('-', '/');
                    this.metadata.coord[provinceKey] = this.metadata.coord[provinceKey] || {};

                    const unitNodes = node.getElementsByTagNameNS(jdipNS || "*",'UNIT');
                    if (unitNodes.length > 0) {
                        const unitNode = unitNodes[0] as Element;
                        const x = getAttribute(unitNode, 'x');
                        const y = getAttribute(unitNode, 'y');
                        if (x && y) this.metadata.coord[provinceKey]!.unit = [x, y];
                    }

                    const dislNodes = node.getElementsByTagNameNS(jdipNS || "*",'DISLODGED_UNIT');
                    if (dislNodes.length > 0) {
                        const dislNode = dislNodes[0] as Element;
                        const x = getAttribute(dislNode, 'x');
                        const y = getAttribute(dislNode, 'y');
                        if (x && y) this.metadata.coord[provinceKey]!.disl = [x, y];
                    }
                }
            }
        }

        // Remove jdipNS nodes after parsing metadata
        const svgNode = doc.getElementsByTagName('svg')[0];
        if (svgNode) {
            const nodesToRemove = [];
            nodesToRemove.push(...Array.from(doc.getElementsByTagNameNS(jdipNS || "*", 'DISPLAY')));
            nodesToRemove.push(...Array.from(doc.getElementsByTagNameNS(jdipNS || "*", 'ORDERDRAWING')));
            nodesToRemove.push(...Array.from(doc.getElementsByTagNameNS(jdipNS || "*", 'PROVINCE_DATA')));

            for (const nodeToRemove of nodesToRemove) {
                if (nodeToRemove.parentNode) {
                    nodeToRemove.parentNode.removeChild(nodeToRemove);
                }
            }
        }
        this.xml_map = serializer.serializeToString(doc);
    }

    public render(incl_orders: boolean = true, incl_abbrev: boolean = false, output_format: string = 'svg', output_path?: string): string | null {
        if (output_format !== 'svg') {
            throw new Error('Only "svg" format is currently supported.');
        }
        if (!this.game || !this.game.map || !this.xml_map) {
            console.warn("Cannot render: game, map, or xml_map not available.");
            return null;
        }

        const parser = new DOMParser();
        let doc = parser.parseFromString(this.xml_map, "image/svg+xml");
        const serializer = new XMLSerializer();

        // Setting phase and note
            return null;
        }

        const parser = new DOMParser();
        const doc = parser.parseFromString(this.xml_map, "text/xml"); // Use text/xml for potentially non-standard SVG
        const serializer = new XMLSerializer();
        const svgEl = doc.documentElement;

        // Clear dynamic layers (OrderLayer, UnitLayer, DislodgedUnitLayer)
        const layerIdsToClear = [LAYER_ORDER, LAYER_UNIT, LAYER_DISL];
        layerIdsToClear.forEach(layerId => {
            const layer = this.findElementById(svgEl, layerId);
            if (layer) {
                while (layer.firstChild) {
                    layer.removeChild(layer.firstChild);
                }
            }
        });

        // Setting phase and note
        const nb_centers_per_power = Object.values(this.game.powers)
            .filter(p => !p.is_eliminated())
            .map(p => ({ name: p.name.substring(0, 3).toUpperCase(), centers: p.centers.length }))
            .sort((a, b) => b.centers - a.centers)
            .map(item => `${item.name}: ${item.centers}`)
            .join(' ');

        this._set_current_phase(doc, this.game.get_current_phase());
        this._set_note(doc, nb_centers_per_power, this.game.note);

        // Adding units and influence
        for (const power of Object.values(this.game.powers)) {
            power.units.forEach(unit => this._add_unit(doc, unit.toString(), power.name, false)); // unit.toString() if Unit class
            power.retreats.forEach(unit => this._add_unit(doc, unit.toString(), power.name, true)); // unit.toString() if Unit class

            power.centers.forEach(center_loc => { // center_loc is a string
                this._set_influence(doc, center_loc, power.name, true);
            });
            // this.game.get_influence() or similar needed for general influence
            // For now, only SC influence is directly available via power.centers
        }

        // TODO: Orders rendering if incl_orders is true

        // Handle province abbreviation layer and mouse layer
        const briefLabelLayer = this.findElementById(svgEl, 'BriefLabelLayer');
        if (briefLabelLayer && !incl_abbrev) {
            briefLabelLayer.parentNode?.removeChild(briefLabelLayer);
        }
        const mouseLayer = this.findElementById(svgEl, 'MouseLayer');
        if (mouseLayer) {
            mouseLayer.parentNode?.removeChild(mouseLayer);
        }

        const rendered_image = serializer.serializeToString(doc);

        if (output_path) {
            fs.writeFileSync(output_path, rendered_image, 'utf-8');
        }
        return rendered_image;
    }

    private findElementById(docOrEl: Document | Element, id: string): Element | null {
        if ('getElementById' in docOrEl && typeof docOrEl.getElementById === 'function') {
            return docOrEl.getElementById(id);
        }
        // Fallback for Elements or if getElementById is not available/reliable on the specific DOM implementation
        const results = docOrEl.getElementsByTagNameNS('*', '*'); // Get all elements
        for(let i=0; i < results.length; i++) {
            const el = results[i] as Element;
            if(getAttribute(el, 'id') === id) return el;
        }
        return null;
    }


    // --- Stubs for other private methods ---
    private _norm_order(order: string): string[] {
        // This should ideally use game logic for full normalization (like Python's game._add_unit_types)
        // For now, using map's compact, which is close.
        return this.game.map.compact(order);
    }

    private _add_unit(doc: Document, unit_str: string, power_name: string, is_dislodged: boolean): void {
        const [unit_type_char, loc] = unit_str.split(/\s+/);
        if (!unit_type_char || !loc) {
            logger.warn(`_add_unit: Could not parse unit string: ${unit_str}`);
            return;
        }
        const unit_type = unit_type_char === 'A' ? ARMY : FLEET; // Assuming 'A' or 'F'

        const coords = is_dislodged ? this.metadata.coord[loc]?.disl : this.metadata.coord[loc]?.unit;
        if (!coords) {
            logger.warn(`_add_unit: No coordinates found for ${loc} (dislodged: ${is_dislodged})`);
            return;
        }
        const [loc_x, loc_y] = coords;
        const symbol_size = this.metadata.symbol_size[unit_type];
        if (!symbol_size) {
            logger.warn(`_add_unit: No symbol size found for ${unit_type}`);
            return;
        }

        const node = doc.createElement('use');
        node.setAttribute('id', `${is_dislodged ? 'dislodged_' : ''}unit_${loc}`);
        node.setAttribute('x', loc_x);
        node.setAttribute('y', loc_y);
        node.setAttribute('height', symbol_size[0]);
        node.setAttribute('width', symbol_size[1]);
        node.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', `#${is_dislodged ? 'Dislodged' : ''}${unit_type}`);
        node.setAttribute('class', `unit${power_name.toLowerCase()}`);

        const layerId = is_dislodged ? LAYER_DISL : LAYER_UNIT;
        const layer = this.findElementById(doc.documentElement, layerId);
        if (layer) {
            layer.appendChild(node);
        } else {
            logger.warn(`_add_unit: Layer ${layerId} not found.`);
        }
    }

    private _set_influence(doc: Document, loc: string, power_name: string, has_supply_center: boolean = false): void {
        const base_loc = loc.substring(0, 3).toUpperCase(); // Ensure base loc for SC check

        if (this.game.map.scs.includes(base_loc) && !has_supply_center) {
            // This logic from Python: if it's an SC but we are not specifically setting SC influence, skip.
            // This is to prevent general influence from overriding specific SC ownership display if they differ.
            return;
        }
        if (this.game.map.get_province_type(base_loc) === 'WATER') { // Use get_province_type for safety
            return;
        }

        const className = power_name ? power_name.toLowerCase() : 'nopower';
        const mapLayer = this.findElementById(doc.documentElement, 'MapLayer');
        if (mapLayer) {
            // Province IDs in SVGs are often like `_par`, `_spa_nc`
            // We need to find the element that represents the land/province area.
            // This could be the element with id `_<loc_lowercase>` or a child of it.
            const provinceElementId = `_${base_loc.toLowerCase()}`; // Try base first
            let provinceElement = this.findElementById(mapLayer, provinceElementId);

            if (!provinceElement && loc.includes('/')) { // Try specific coast like _spa_sc
                 provinceElement = this.findElementById(mapLayer, `_${loc.toLowerCase().replace('/', '_')}`);
            }

            if (provinceElement) {
                if (['path', 'polygon', 'rect', 'circle'].includes(provinceElement.nodeName.toLowerCase())) {
                    provinceElement.setAttribute('class', className);
                } else if (provinceElement.nodeName.toLowerCase() === 'g') { // Group of paths
                    let edited = false;
                    for(let i=0; i < provinceElement.childNodes.length; i++) {
                        const subNode = provinceElement.childNodes[i] as Element;
                        if(subNode.nodeType === 1 && ['path', 'polygon', 'rect', 'circle'].includes(subNode.nodeName.toLowerCase())) {
                            if (getAttribute(subNode, 'class') !== 'water') { // Don't change class of water elements within a group
                                subNode.setAttribute('class', className);
                                edited = true;
                            }
                        }
                    }
                    // if (!edited) provinceElement.setAttribute('class', className); // Fallback for group itself if no suitable children
                }
            } else {
                logger.warn(`_set_influence: Province element for ${loc} (tried ${provinceElementId}) not found.`);
            }
        }
    }

    private _set_current_phase(doc: Document, current_phase_str: string): void {
        const phaseTextElement = this.findElementById(doc.documentElement, 'CurrentPhase');
        if (phaseTextElement) {
            const displayPhase = (current_phase_str[0] === '?' || current_phase_str === 'COMPLETED') ? 'FINAL' : current_phase_str;
            phaseTextElement.textContent = displayPhase;
        } else {
            logger.warn("_set_current_phase: Element with ID 'CurrentPhase' not found.");
        }
    }

    private _set_note(doc: Document, note_1: string, note_2: string | null): void {
        const note1Element = this.findElementById(doc.documentElement, 'CurrentNote');
        if (note1Element) {
            note1Element.textContent = note_1 || ' ';
        }
        const note2Element = this.findElementById(doc.documentElement, 'CurrentNote2');
        if (note2Element) {
            note2Element.textContent = note_2 || ' ';
        }
    }

    // Stubs for _issue_*_order methods
    private _issue_hold_order(doc: Document, loc: string, power_name: string): void { console.warn("_issue_hold_order is a stub.");  }
    private _issue_support_hold_order(doc: Document, loc: string, dest_loc: string, power_name: string): void { console.warn("_issue_support_hold_order is a stub.");  }
    private _issue_move_order(doc: Document, src_loc: string, dest_loc: string, power_name: string): void { console.warn("_issue_move_order is a stub.");  }
    private _issue_support_move_order(doc: Document, loc: string, src_loc: string, dest_loc: string, power_name: string): void { console.warn("_issue_support_move_order is a stub.");  }
    private _issue_convoy_order(doc: Document, loc: string, src_loc: string, dest_loc: string, power_name: string): void { console.warn("_issue_convoy_order is a stub.");  }
    private _issue_build_order(doc: Document, unit_type: string, loc: string, power_name: string): void { console.warn("_issue_build_order is a stub.");  }
    private _issue_disband_order(doc: Document, loc: string): void { console.warn("_issue_disband_order is a stub.");  }

    // Coordinate and stroke width helpers
    private _center_symbol_around_unit(loc: string, is_dislodged: boolean, symbol_name: string): [string, string] {
        const key = is_dislodged ? 'disl' : 'unit';
        const unit_coords = this.metadata.coord[loc]?.[key];
        const unit_size_info = this.metadata.symbol_size[ARMY]; // Base size on Army symbol
        const symbol_size_info = this.metadata.symbol_size[symbol_name];

        if (!unit_coords || !unit_size_info || !symbol_size_info) {
            logger.warn(`_center_symbol_around_unit: Missing metadata for ${loc}, dislodged: ${is_dislodged}, symbol: ${symbol_name}`);
            return ["0", "0"];
        }
        const unit_x = parseFloat(unit_coords[0]);
        const unit_y = parseFloat(unit_coords[1]);
        const unit_width = parseFloat(unit_size_info[1]);
        const unit_height = parseFloat(unit_size_info[0]);
        const symbol_width = parseFloat(symbol_size_info[1]);
        const symbol_height = parseFloat(symbol_size_info[0]);

        return [
            (unit_x + unit_width / 2 - symbol_width / 2).toString(),
            (unit_y + unit_height / 2 - symbol_height / 2).toString()
        ];
    }
    private _get_unit_center(loc: string, is_dislodged: boolean): [number, number] {
        const key = is_dislodged ? 'disl' : 'unit';
        const unit_coords = this.metadata.coord[loc]?.[key];
        // Assuming ARMY symbol size is representative for unit centering, adjust if FLEET has different center logic.
        const unit_size_info = this.metadata.symbol_size[ARMY];
        if (!unit_coords || !unit_size_info) {
             logger.warn(`_get_unit_center: Missing metadata for ${loc}, dislodged: ${is_dislodged}`);
            return [0,0];
        }
        return [
            parseFloat(unit_coords[0]) + parseFloat(unit_size_info[1]) / 2,
            parseFloat(unit_coords[1]) + parseFloat(unit_size_info[0]) / 2
        ];
    }
    private _plain_stroke_width(): number {
        return parseFloat(this.metadata.symbol_size?.Stroke?.[0] || "1");
    }
    private _colored_stroke_width(): number {
        return parseFloat(this.metadata.symbol_size?.Stroke?.[1] || "1");
    }

}

// Placeholder for EquilateralTriangle if needed by order drawing.
// class EquilateralTriangle { constructor(...args: any[]) {} intersection(x: number, y: number): [number, number] { return [x,y];} }
