import React from "react";
import PropTypes from "prop-types";
import { PhaseSummaryView } from "./phase_summary_view"; // Import named export

export class PhaseSummaryBottomSheet extends React.Component {
    componentDidUpdate(prevProps) {
        if (prevProps.phase !== this.props.phase) {
            console.log(
                "[PhaseSummaryBottomSheet Debug] Phase prop changed from",
                prevProps.phase,
                "to",
                this.props.phase
            );
        }
    }

    render() {
        const { phase, summaryText, visible, onClose } = this.props;

        if (!visible) {
            return null;
        }

        const bottomSheetStyle = {
            position: 'fixed',
            bottom: 0,
            left: 0,
            width: '100%',
            backgroundColor: 'white',
            borderTop: '1px solid #ccc',
            padding: '20px',
            boxShadow: '0px -2px 5px rgba(0, 0, 0, 0.1)',
            zIndex: 1000,
            maxHeight: '40vh',
            overflowY: 'auto'
        };

        return (
            <div style={bottomSheetStyle}>
                {/* <div style={{ fontStyle: 'italic', color: 'gray' }}>
                  Debug: Currently showing summary for phase: {phase}
                </div> */}
                <PhaseSummaryView phase={phase} summaryText={summaryText} />
                <button
                    onClick={onClose}
                    style={{
                        position: 'absolute',
                        top: '10px',
                        right: '10px',
                        padding: '5px 10px'
                    }}
                >
                    Close
                </button>
            </div>
        );
    }
}

PhaseSummaryBottomSheet.propTypes = {
    phase: PropTypes.string.isRequired,
    summaryText: PropTypes.string,
    visible: PropTypes.bool,
    onClose: PropTypes.func.isRequired
};

PhaseSummaryBottomSheet.defaultProps = {
    visible: false,
    summaryText: ""
};