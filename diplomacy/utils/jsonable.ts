// diplomacy/utils/jsonable.ts
/**
 * Abstract Jsonable class with automatic attributes checking and conversion to/from JSON dict.
 * To write a Jsonable sub-class:
 *
 * - Define a static `model` with expected attribute names and their types/validation logic.
 * - Override the constructor:
 *     - Initialize each attribute defined in the model with a default value (e.g., null, undefined).
 *     - Call `super(kwargs)` to have attributes checked and filled.
 *     - Add further initialization code after the call to the parent constructor if needed.
 */

import * as exceptions from './exceptions';
import {
    validate_data as parsing_validate_data,
    update_data as parsing_update_data,
    to_json as parsing_to_json,
    to_type as parsing_to_type
} from './parsing'; // Import actual functions

const logger = {
    error: (message: string, ...args: any[]) => console.error('[Jsonable]', message, ...args),
    warn: (message: string, ...args: any[]) => console.warn('[Jsonable]', message, ...args),
};

export abstract class Jsonable {
    // Descendant classes should define this static model.
    // Example: static model = { my_attribute: 'string', count: 'number' };
    // For more complex types, the string could be a key to a parsing function or class.
    static model: Record<string, any> = {};

    constructor(kwargs: Record<string, any> = {}) {
        const model = (this.constructor as typeof Jsonable).getModel();

        // Initialize attributes defined in the model to null or undefined first
        for (const model_key in model) {
            if (model.hasOwnProperty(model_key)) {
                (this as any)[model_key] = undefined;
            }
        }

        const updated_kwargs: Record<string, any> = {};
        for (const model_key in model) {
            updated_kwargs[model_key] = undefined; // Or a default from model if specified
        }
        Object.assign(updated_kwargs, kwargs);


        try {
            // Placeholder for Python's parsing.validate_data
            // In TS, this would often be handled by constructor types or dedicated validation methods.
            parsing_validate_data(updated_kwargs, model);
        } catch (exception: any) {
            logger.error(`Error occurred while building class ${this.constructor.name}`);
            throw exception;
        }

        // Placeholder for Python's parsing.update_data (e.g. for default values)
        const final_attrs = parsing_update_data(updated_kwargs, model);

        for (const model_key in model) {
            if (final_attrs.hasOwnProperty(model_key)) {
                (this as any)[model_key] = final_attrs[model_key];
            }
        }
    }

    toJsonString(): string {
        return JSON.stringify(this.toDict());
    }

    toDict(): Record<string, any> {
        const model = (this.constructor as typeof Jsonable).getModel();
        const dict: Record<string, any> = {};
        for (const key in model) {
            if (model.hasOwnProperty(key) && typeof (this as any)[key] !== 'function') {
                 // Ensure the property exists on 'this' before trying to access it
                if (Object.prototype.hasOwnProperty.call(this, key)) {
                    dict[key] = parsing_to_json((this as any)[key], model[key]);
                } else {
                    // Handle cases where model key might not be an actual property (e.g. if using getters without direct props)
                    // Or if it was initialized to undefined and should be represented as null/undefined in dict.
                    dict[key] = parsing_to_json(undefined, model[key]);
                }
            }
        }
        return dict;
    }

    /**
     * Optional hook for subclasses to update/process the JSON dictionary
     * before it's used to create an instance.
     * @param jsonDict The JSON dictionary.
     */
    static updateJsonDict?(jsonDict: Record<string, any>): void;

    static fromDict<T extends Jsonable>(
        this: {
            new (...args: any[]): T;
            getModel(): Record<string, any>;
            updateJsonDict?(jsonDict: Record<string, any>): void;
        },
        jsonDict: Record<string, any>
    ): T {
        if (typeof jsonDict !== 'object' || jsonDict === null) {
            throw new exceptions.TypeException('object', typeof jsonDict);
        }

        const model = this.getModel();
        const default_json_dict: Record<string, any> = {};
        for (const key in model) {
            default_json_dict[key] = null; // Or handle defaults from model more explicitly
        }
        Object.assign(default_json_dict, jsonDict);

        if (typeof this.updateJsonDict === 'function') {
            this.updateJsonDict(default_json_dict); // Allow class to modify dict before parsing
        }

        const kwargs: Record<string, any> = {};
        for (const key in model) {
            if (model.hasOwnProperty(key)) {
                 // Ensure key exists in default_json_dict before parsing, even if it's null/undefined
                kwargs[key] = parsing_to_type(default_json_dict[key], model[key]);
            }
        }
        return new this(kwargs);
    }

    static fromJsonString<T extends Jsonable>(
        this: {
            new (...args: any[]): T;
            fromDict(jsonDict: Record<string, any>): T;
            getModel(): Record<string, any>;
            updateJsonDict?(jsonDict: Record<string, any>): void;
        },
        jsonStr: string
    ): T {
        return this.fromDict(JSON.parse(jsonStr));
    }

    /**
     * Descendant classes must implement this to provide their specific model.
     * Or they can override the static `model` property directly.
     */
    static getModel(): Record<string, any> {
        // This default implementation relies on `static model` being defined on the subclass.
        // Caching logic from Python's get_model is omitted for simplicity here,
        // as direct static property access is common in TS/JS.
        return this.model || {};
    }
}
