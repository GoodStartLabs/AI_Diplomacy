import React from "react";
import PropTypes from "prop-types";

export class PhaseSummaryView extends React.Component {
    render() {
        const { phase, summaryText } = this.props;
        console.log("PhaseSummaryView props", this.props)
        if (!summaryText) {
            return null;  // or some fallback message
        }

        return (
            <div className="phase-summary row">
                <div className="col-sm-12">
                    <h5>Summary for {phase}:</h5>
                    <div className="phase-summary-body">
                        {summaryText}
                    </div>
                </div>
            </div>
        );
    }
}

PhaseSummaryView.propTypes = {
    phase: PropTypes.string.isRequired,
    summaryText: PropTypes.string
};