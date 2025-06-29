// ==============================================================================
// Copyright (C) 2019 - Philip Paquette, Steven Bocco
//
//  This program is free software: you can redistribute it and/or modify it under
//  the terms of the GNU Affero General Public License as published by the Free
//  Software Foundation, either version 3 of the License, or (at your option) any
//  later version.
//
//  This program is distributed in the hope that it will be useful, but WITHOUT
//  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
//  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
//  details.
//
//  You should have received a copy of the GNU Affero General Public License along
//  with this program.  If not, see <https://www.gnu.org/licenses/>.
// ==============================================================================
import React from "react";
import {UTILS} from "../../diplomacy/utils/utils";
import {Button} from "./button";

export class Forms {
    static createOnChangeCallback(component, callback) {
        return (event) => {
            const value = UTILS.html.isCheckBox(event.target) ? event.target.checked : event.target.value;
            const fieldName = UTILS.html.isRadioButton(event.target) ? event.target.name : event.target.id;
            const update = {[fieldName]: value};
            const state = Object.assign({}, component.state, update);
            if (callback)
                callback(state);
            component.setState(state);
        };
    }

    static createOnSubmitCallback(component, callback, resetState) {
        return (event) => {
            if (callback)
                callback(Object.assign({}, component.state));
            if (resetState)
                component.setState(resetState);
            event.preventDefault();
        };
    }

    static createOnResetCallback(component, onChangeCallback, resetState) {
        return (event) => {
            if (onChangeCallback)
                onChangeCallback(resetState);
            component.setState(resetState);
            if (event && event.preventDefault)
                event.preventDefault();
        };
    }

    static getValue(fieldValues, fieldName, defaultValue) {
        return fieldValues.hasOwnProperty(fieldName) ? fieldValues[fieldName] : defaultValue;
    }

    static createReset(title, large, onReset) {
        return <Button key={'reset'} title={title || 'reset'} onClick={onReset} pickEvent={true} large={large}/>;
    }

    static createSubmit(title, large, onSubmit) {
        return <Button key={'submit'} title={title || 'submit'} onClick={onSubmit} pickEvent={true} large={large}/>;
    }

    static createButton(title, fn, color, large) {
        const wrapFn = (event) => {
            fn();
            event.preventDefault();
        };
        return <Button large={large} key={title} color={color} title={title} onClick={wrapFn} pickEvent={true}/>;
    }

    static createCheckbox(id, title, value, onChange) {
        const input = <input className={'form-check-input'} key={id} type={'checkbox'} id={id} checked={value}
                             onChange={onChange}/>;
        const label = <label className={'form-check-label'} key={`label-${id}`} htmlFor={id}>{title}</label>;
        return [input, label];
    }

    static createRadio(name, value, title, currentValue, onChange) {
        const id = `[${name}][${value}]`;
        const input = <input className={'form-check-input'} key={id} type={'radio'}
                             name={name} value={value} checked={currentValue === value}
                             id={id} onChange={onChange}/>;
        const label = <label className={'form-check-label'} key={`label-${id}`} htmlFor={id}>{title || value}</label>;
        return [input, label];
    }

    static createRow(label, input) {
        return (
            <div className={'form-group row'}>
                {label}
                <div className={'col'}>{input}</div>
            </div>
        );
    }

    static createLabel(htmFor, title, className) {
        return <label className={className} htmlFor={htmFor}>{title}</label>;
    }

    static createColLabel(htmlFor, title) {
        return Forms.createLabel(htmlFor, title, 'col');
    }

    static createSelectOptions(values, none) {
        const options = values.slice();
        const components = options.map((option, index) => <option key={index} value={option}>{option}</option>);
        if (none) {
            components.splice(0, 0, [<option key={-1} value={''}>{none === true ? '(none)' : `${none}`}</option>]);
        }
        return components;
    }
}

