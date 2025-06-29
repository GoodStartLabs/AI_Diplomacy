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
import {FancyBox} from "../../components/fancyBox";
import PropTypes from "prop-types";
import Octicon, {ArrowLeft} from "@primer/octicons-react";

export class PanelChoosePower extends React.Component {
    render() {
        this.props.powers.sort();
        return (
            <FancyBox title={'Choose your power'} onClose={this.props.cancel}>
                <div className="row">
                    <div className="col-sm">
                        <button type="button" className="btn btn-secondary btn-sm btn-block inline" onClick={() => {
                            this.props.onUpdateParams({power_name: null});
                            this.props.forward();
                        }}>I just want to observe
                        </button>
                    </div>
                    <div className="col-sm">
                        <button type="button" className="btn btn-secondary btn-sm btn-block inline" onClick={() => {
                            const powerName = this.props.powers[Math.floor(Math.random() * this.props.powers.length)];
                            this.props.onUpdateParams({power_name: powerName});
                            this.props.forward();
                        }}>Choose randomly for me
                        </button>
                    </div>
                </div>
                <div className="row">
                    <div className="col">
                        <div className="d-flex flex-row justify-content-center my-2">
                            {(() => {
                                const choice = [];
                                for (let i = 0; i < this.props.powers.length; ++i) {
                                    choice.push(
                                        <button key={i} type="button"
                                                className={`btn btn-secondary btn-sm flex-grow-1 ${i === 0 ? '' : 'ml-sm-1'}`}
                                                onClick={() => {
                                                    this.props.onUpdateParams({power_name: this.props.powers[i]});
                                                    this.props.forward();
                                                }}>
                                            {this.props.powers[i]}
                                        </button>
                                    );
                                }
                                return choice;
                            })()}
                        </div>
                    </div>
                </div>
                <div className="row">
                    <div className="col">
                        <button type="button" className="btn btn-secondary btn-sm px-3"
                                onClick={() => this.props.backward()}>
                            <Octicon icon={ArrowLeft}/>
                        </button>
                    </div>
                </div>
            </FancyBox>
        );
    }
}

PanelChoosePower.propTypes = {
    backward: PropTypes.func.isRequired,
    forward: PropTypes.func.isRequired,
    cancel: PropTypes.func.isRequired,
    onUpdateParams: PropTypes.func.isRequired,
    powers: PropTypes.arrayOf(PropTypes.string).isRequired
};
