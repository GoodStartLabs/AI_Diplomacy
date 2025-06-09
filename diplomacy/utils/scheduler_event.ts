// diplomacy/utils/scheduler_event.ts
// Scheduler event describing scheduler state for a specific data.

import { Jsonable } from './jsonable';
import { PrimitiveType } from './parsing'; // Using PrimitiveType for clarity in model

export interface SchedulerEventData {
    time_unit: number;
    time_added: number;
    delay: number;
    current_time: number;
}

export class SchedulerEvent extends Jsonable {
    public time_unit: number;
    public time_added: number;
    public delay: number;
    public current_time: number;

    // Define the model for Jsonable serialization/deserialization
    static model: Record<string, any> = {
        'time_unit': new PrimitiveType(Number),
        'time_added': new PrimitiveType(Number),
        'delay': new PrimitiveType(Number),
        'current_time': new PrimitiveType(Number)
    };

    constructor(kwargs: Partial<SchedulerEventData> = {}) {
        // Initialize properties to default values first
        this.time_unit = 0;
        this.time_added = 0;
        this.delay = 0;
        this.current_time = 0;

        // Let Jsonable constructor handle kwargs based on the model
        super(kwargs);
    }
}
