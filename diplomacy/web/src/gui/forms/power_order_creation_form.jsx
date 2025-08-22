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
import React from 'react';
import {Forms} from "../components/forms";
import {ORDER_BUILDER} from "../utils/order_building";
import {STRINGS} from "../../diplomacy/utils/strings";
import PropTypes from "prop-types";
import {Power} from "../../diplomacy/engine/power";


export class PowerOrderCreationForm extends React.Component {
    componentDidMount() {
        document.addEventListener('keydown', this.handleKeyDown);
    }

    componentWillUnmount() {
        document.removeEventListener('keydown', this.handleKeyDown);
    }

    handleKeyDown = (event) => {
        const key = event.key.toLowerCase();
        if (key === 'escape') {
            event.preventDefault();
            this.setState(this.initState(), () => {
                if (this.props.onChange)
                    this.props.onChange(this.state);
            });
        } else if (this.props.orderTypes.includes(key.toUpperCase())) {
            event.preventDefault();
            this.setState({order_type: key.toUpperCase()}, () => {
                if (this.props.onChange)
                    this.props.onChange(this.state);
            });
        }
    };

    constructor(props) {
        super(props);
        this.state = this.initState();
    }

    initState() {
        return {order_type: this.props.orderType};
    }

    render() {
        const onChange = Forms.createOnChangeCallback(this, this.props.onChange);
        const onReset = Forms.createOnResetCallback(this, this.props.onChange, this.initState());
        let title = '';
        let titleClass = 'mr-4';
        const header = [];
        const votes = [];
        if (this.props.orderTypes.length) {
            title = 'Create order:';
            header.push(...this.props.orderTypes.map((orderLetter, index) => (
                <div key={index} className={'form-check-inline'}>
                    {Forms.createRadio('order_type', orderLetter, ORDER_BUILDER[orderLetter].name, this.props.orderType, onChange)}
                </div>
            )));
            header.push(Forms.createReset('reset', false, onReset));
        } else if (this.props.power.order_is_set) {
            title = 'Unorderable power.';
            titleClass += ' neutral';
        } else {
            title = 'No orders available for this power.';
        }
        if (!this.props.power.order_is_set) {
            header.push(Forms.createButton('pass', this.props.onPass));
        }

        if (this.props.role !== STRINGS.OMNISCIENT_TYPE) {
            votes.push(<strong key={0} className={'ml-4 mr-2'}>Vote for draw:</strong>);
            switch (this.props.power.vote) {
                case 'yes':
                    votes.push(Forms.createButton('no', () => this.props.onVote('no'), 'danger'));
                    votes.push(Forms.createButton('neutral', () => this.props.onVote('neutral'), 'info'));
                    break;
                case 'no':
                    votes.push(Forms.createButton('yes', () => this.props.onVote('yes'), 'success'));
                    votes.push(Forms.createButton('neutral', () => this.props.onVote('neutral'), 'info'));
                    break;
                case 'neutral':
                    votes.push(Forms.createButton('yes', () => this.props.onVote('yes'), 'success'));
                    votes.push(Forms.createButton('no', () => this.props.onVote('no'), 'danger'));
                    break;
                default:
                    votes.push(Forms.createButton('yes', () => this.props.onVote('yes'), 'success'));
                    votes.push(Forms.createButton('no', () => this.props.onVote('no'), 'danger'));
                    votes.push(Forms.createButton('neutral', () => this.props.onVote('neutral'), 'info'));
                    break;
            }
        }
        return (
            <div>
                <div><strong key={'title'} className={titleClass}>{title}</strong></div>
                <form className={'form-inline power-actions-form'}>
                    {header}
                    {Forms.createButton(
                        (this.props.power.wait ? 'no wait' : 'wait'),
                        this.props.onSetWaitFlag,
                        (this.props.power.wait ? 'success' : 'danger')
                    )}
                    {votes}
                </form>
            </div>
        );
    }
}

PowerOrderCreationForm.propTypes = {
    orderType: PropTypes.oneOf(Object.keys(ORDER_BUILDER)),
    orderTypes: PropTypes.arrayOf(PropTypes.oneOf(Object.keys(ORDER_BUILDER))),
    power: PropTypes.instanceOf(Power),
    role: PropTypes.string,
    onChange: PropTypes.func,
    onSubmit: PropTypes.func,
    onPass: PropTypes.func, // onPass(), to submit empty orders set (powers want to do nothing at this phase)
    onVote: PropTypes.func, // onVote(voteString)
    onSetWaitFlag: PropTypes.func, // onSetWaitFlag(),
};
