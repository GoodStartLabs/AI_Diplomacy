// diplomacy/server/scheduler.ts

import { SchedulerEvent } from '../utils/scheduler_event';
import { NaturalIntegerException, NaturalIntegerNotNullException, AlreadyScheduledException } from '../utils/exceptions';
import { PriorityDict } from '../utils/priority_dict'; // Assuming this is a MinPriorityQueue

// --- Helper for async sleep ---
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// --- Basic Async Mutex ---
class AsyncMutex {
    private locked = false;
    private queue: (() => void)[] = [];

    async acquire(): Promise<void> {
        return new Promise(resolve => {
            if (!this.locked) {
                this.locked = true;
                resolve();
            } else {
                this.queue.push(resolve);
            }
        });
    }

    release(): void {
        if (this.queue.length > 0) {
            const nextResolve = this.queue.shift();
            if (nextResolve) {
                // This keeps the lock acquired for the next in queue
                nextResolve();
            } else {
                 this.locked = false; // Should not happen if queue had items
            }
        } else {
            this.locked = false;
        }
    }

    async withLock<T>(fn: () => Promise<T>): Promise<T> {
        await this.acquire();
        try {
            return await fn();
        } finally {
            this.release();
        }
    }
}


class Deadline {
    public start_time: number;
    public delay: number;

    constructor(start_time: number, delay: number) {
        this.start_time = start_time;
        this.delay = delay;
    }

    get deadline(): number {
        return this.start_time + this.delay;
    }

    toString(): string {
        return `Deadline(${this.start_time} + ${this.delay} = ${this.deadline})`;
    }

    // For PriorityDict comparison: lower deadline value means higher priority
    valueOf(): number {
        return this.deadline;
    }
}

class Task {
    public data: any;
    public deadline: Deadline;
    public valid: boolean = true;

    constructor(data: any, deadline: Deadline) {
        this.data = data;
        this.deadline = deadline;
    }

    toString(): string {
        return `${this.constructor.name}(${this.data?.constructor?.name || typeof this.data}, ${this.deadline})`;
    }

    update_delay(new_delay: number): void {
        this.deadline.delay = new_delay;
    }
}

class ImmediateTask extends Task {
    private validator: () => boolean;

    constructor(data: any, future_delay: number, processing_validator: boolean | ((data: any) => boolean)) {
        super(data, new Deadline(-future_delay, future_delay)); // deadline effectively 0 for first processing
        if (typeof processing_validator === 'boolean') {
            this.validator = () => processing_validator;
        } else if (typeof processing_validator === 'function') {
            this.validator = () => processing_validator(data);
        } else {
            throw new Error('Validator for immediate task must be either a boolean or a callback(data).');
        }
    }

    can_still_process(): boolean {
        return this.validator();
    }

    override update_delay(new_delay: number): void {
        this.deadline.start_time = -new_delay; // Ensure deadline is 0 if new_delay is 0 for next immediate processing
        this.deadline.delay = new_delay;
    }
}

export class Scheduler {
    public unit: number; // unit_in_seconds
    public current_time: number = 0;
    private callback_process: (data: any) => Promise<boolean> | boolean;
    private data_in_heap: PriorityDict<any, Deadline>; // data => Deadline
    private data_in_queue: Map<any, Task>; // data => Task in queue
    private tasks_queue: Task[] = []; // Simple array as a queue
    private lock: AsyncMutex = new AsyncMutex();
    private processing: boolean = false; // To control process_tasks loop
    private scheduling: boolean = false; // To control schedule loop

    constructor(unit_in_seconds: number, callback_process: (data: any) => Promise<boolean> | boolean) {
        if (!(typeof unit_in_seconds === 'number' && unit_in_seconds > 0 && Number.isInteger(unit_in_seconds))) {
            throw new Error("unit_in_seconds must be a positive integer.");
        }
        if (typeof callback_process !== 'function') {
            throw new Error("callback_process must be a function.");
        }
        this.unit = unit_in_seconds;
        this.callback_process = callback_process;
        this.data_in_heap = new PriorityDict<any, Deadline>();
        this.data_in_queue = new Map<any, Task>();
    }

    private _enqueue(task: Task): void {
        this.data_in_queue.set(task.data, task);
        this.tasks_queue.push(task);
        // If process_tasks is not running, kick it off (non-blocking)
        if (!this.processing && this.scheduling) { // Only start processing if scheduler is active
             this.process_tasks().catch(err => console.error("Error in process_tasks loop:", err));
        }
    }

    public async has_data(data: any): Promise<boolean> {
        return this.lock.withLock(async () => {
            return this.data_in_heap.has(data) || this.data_in_queue.has(data);
        });
    }

    public async get_info(data: any): Promise<SchedulerEvent | null> {
        return this.lock.withLock(async () => {
            let deadline_obj: Deadline | undefined;
            if (this.data_in_heap.has(data)) {
                deadline_obj = this.data_in_heap.get(data);
            } else if (this.data_in_queue.has(data)) {
                deadline_obj = this.data_in_queue.get(data)!.deadline;
            }

            if (deadline_obj) {
                return new SchedulerEvent(this.unit, deadline_obj.start_time, deadline_obj.delay, this.current_time);
            }
            return null;
        });
    }

    public async add_data(data: any, nb_units_to_wait: number): Promise<void> {
        if (!(Number.isInteger(nb_units_to_wait) && nb_units_to_wait > 0)) {
            throw new NaturalIntegerNotNullException("nb_units_to_wait must be a positive integer.");
        }
        await this.lock.withLock(async () => {
            if (this.data_in_heap.has(data) || this.data_in_queue.has(data)) {
                throw new AlreadyScheduledException("Data is already scheduled.");
            }
            this.data_in_heap.set(data, new Deadline(this.current_time, nb_units_to_wait));
        });
    }

    public async no_wait(data: any, nb_units_to_wait_after_first: number, processing_validator: boolean | ((d: any) => boolean)): Promise<void> {
        if (!(Number.isInteger(nb_units_to_wait_after_first) && nb_units_to_wait_after_first >= 0)) {
            throw new NaturalIntegerException("nb_units_to_wait_after_first must be a non-negative integer.");
        }
        await this.lock.withLock(async () => {
            if (this.data_in_heap.has(data)) {
                this.data_in_heap.delete(data); // Remove from heap
                this._enqueue(new ImmediateTask(data, nb_units_to_wait_after_first, processing_validator));
            } else if (this.data_in_queue.has(data)) {
                const task = this.data_in_queue.get(data)!;
                task.update_delay(nb_units_to_wait_after_first); // Update future delay
            } else {
                this._enqueue(new ImmediateTask(data, nb_units_to_wait_after_first, processing_validator));
            }
        });
    }

    public async remove_data(data: any): Promise<void> {
        await this.lock.withLock(async () => {
            if (this.data_in_heap.has(data)) {
                this.data_in_heap.delete(data);
            } else if (this.data_in_queue.has(data)) {
                const task = this.data_in_queue.get(data)!;
                task.valid = false; // Mark as invalid, process_tasks will ignore it
                this.data_in_queue.delete(data);
            }
        });
    }

    private async _step(): Promise<void> {
        await this.lock.withLock(async () => {
            this.current_time += 1;
            while (!this.data_in_heap.isEmpty()) {
                const data = this.data_in_heap.peek(); // PriorityDict needs peek or similar
                const deadline_obj = this.data_in_heap.get(data!)!; // data cannot be undefined if not empty

                if (deadline_obj.deadline > this.current_time) {
                    break;
                }
                this.data_in_heap.pop(); // Removes and returns smallest, but we already have it
                this._enqueue(new Task(data, deadline_obj));
            }
        });
    }

    public async schedule(): Promise<void> {
        if (this.scheduling) return; // Prevent multiple loops
        this.scheduling = true;
        console.log("Scheduler started.");
        // Kick off task processing loop if not already running
        if(!this.processing) {
            this.process_tasks().catch(err => {
                 console.error("Error in process_tasks supervisor:", err);
                 this.processing = false; // Allow restart
            });
        }

        while (this.scheduling) {
            await sleep(this.unit * 1000);
            if (!this.scheduling) break; // Check again after sleep
            await this._step();
        }
        console.log("Scheduler stopped.");
    }

    public async process_tasks(): Promise<void> {
        if (this.processing) return; // Prevent multiple loops
        this.processing = true;

        while (this.scheduling || this.tasks_queue.length > 0) { // Process remaining tasks even if scheduling stops
            if (this.tasks_queue.length === 0) {
                if (!this.scheduling) break; // Exit if not scheduling and queue is empty
                await sleep(50); // Short sleep if queue is empty but still scheduling
                continue;
            }
            const task = this.tasks_queue.shift()!;

            try {
                if (task.valid) { // Check if task was invalidated by remove_data
                    let remove_data_flag = false;
                    if (task instanceof ImmediateTask) {
                        if (!task.can_still_process()) {
                            await this.lock.withLock(async () => { // Ensure atomicity for map modification
                                this.data_in_queue.delete(task.data);
                            });
                            continue; // Skip processing and rescheduling
                        }
                    }

                    const result = this.callback_process(task.data);
                    if (typeof result === 'boolean') {
                        remove_data_flag = result;
                    } else {
                        remove_data_flag = await result;
                    }

                    remove_data_flag = remove_data_flag || !task.deadline.delay;

                    await this.lock.withLock(async () => {
                        // Task might have been removed from data_in_queue by remove_data while callback was processing
                        if (this.data_in_queue.get(task.data) === task) {
                           this.data_in_queue.delete(task.data);
                        }
                        if (!remove_data_flag && task.valid) { // Reschedule if not done and still valid
                            this.data_in_heap.set(task.data, new Deadline(this.current_time, task.deadline.delay));
                        }
                    });
                } else { // Task was invalidated (removed) while in queue
                     await this.lock.withLock(async () => {
                        this.data_in_queue.delete(task.data); // Ensure it's removed from tracking map
                     });
                }
            } catch (error) {
                console.error("Error processing task:", task.data, error);
                // Decide if task should be rescheduled or dropped on error
                 await this.lock.withLock(async () => { // Ensure atomicity for map modification
                    this.data_in_queue.delete(task.data);
                 });
            }
        }
        this.processing = false;
        console.log("Task processing loop ended.");
    }

    public stop(): void {
        console.log("Stopping scheduler...");
        this.scheduling = false;
        // Note: This will stop the schedule() loop.
        // The process_tasks() loop will continue until the tasks_queue is empty.
    }
}
