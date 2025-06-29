# ==============================================================================
# Copyright (C) 2019 - Philip Paquette, Steven Bocco
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
""" Scheduler used by server to run games.

    Scheduler is configured with a task manager (callback function) and a step time (in seconds)
    which indicates how long it must wait at each step before checking tasks to process.
    Then, to add a task, user must specify a data to process and a delay (in number of step times).
    Deadline is computed using given delay + scheduler step when data was added.

    To set unit as a minute, create Scheduler with unit_in_seconds = 60.
        In such case, a task with deadline 2 means 2 minutes to wait to process this task.
    To set unit as a second, create Scheduler with unit_in_seconds = 1.
        In such case, a task with deadline 2 means 2 seconds to wait to process this task.
"""
from tornado import gen
from tornado.locks import Lock
from tornado.queues import Queue

from diplomacy.utils.scheduler_event import SchedulerEvent
from diplomacy.utils import exceptions
from diplomacy.utils.priority_dict import PriorityDict

class _Deadline:
    """ (internal) Deadline value, defined by a start time and a delay, such that deadline = start time + delay. """
    __slots__ = ['start_time', 'delay']

    def __init__(self, start_time, delay):
        """ Initialize a deadline with start time and delay, so that deadline = start time + delay.

            :param start_time: (int)
            :param delay:  (int)
        """
        self.start_time = start_time
        self.delay = delay

    @property
    def deadline(self):
        """ Compute and return deadline. """
        return self.start_time + self.delay

    def __str__(self):
        return 'Deadline(%d + %d = %d)' % (self.start_time, self.delay, self.deadline)

    def __lt__(self, other):
        return self.deadline < other.deadline

class _Task:
    """ (internal) Task class used by scheduler to order scheduled data.
        It allows auto-rescheduling of a task after it was processed, until either:

        - task delay is 0.
        - task manager return a True boolean value (means "data fully processed").
        - scheduler is explicitly required to remove associated data.
     """
    __slots__ = ['data', 'deadline', 'valid']

    def __init__(self, data, deadline):
        """ Initialize a task.

            :param data: data to process.
            :param deadline: Deadline object.
            :type deadline: _Deadline
        """
        self.data = data
        self.deadline = deadline
        self.valid = True  # Used to ease task removal from Tornado queue.

    def __str__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, type(self.data).__name__, self.deadline)

    def update_delay(self, new_delay):
        """ Change deadline delay with given new delay. """
        self.deadline.delay = new_delay

class _ImmediateTask(_Task):
    """ (internal) Represents a task intended to be processed as soon as possible the first time,
        and then scheduled as a normal task for next times. As deadline does not matter for first
        processing, an immediate task needs a processing validator called the first
        time to check if it must still be processed. Note that, if validation returns False,
        the task is not processed the first time and not even added to scheduler for next times.
    """
    __slots__ = ['validator']

    def __init__(self, data, future_delay, processing_validator):
        """ Initialize an immediate task.

            :param data: data to process.
            :param future_delay: delay to use to reschedule that task after first processing.
            :param processing_validator: either a Bool or a callable receiving the data and
                returning a Bool: processing_validator(data) -> Bool.
                Validator is used only for the first processing. If evaluated to True, task is
                processed and then rescheduled for next processing with given future delay.
                If evaluated to False, task is drop (neither processed nor rescheduled).
        """
        super(_ImmediateTask, self).__init__(data, _Deadline(-future_delay, future_delay))
        if isinstance(processing_validator, bool):
            self.validator = lambda: processing_validator
        elif callable(processing_validator):
            self.validator = lambda: processing_validator(data)
        else:
            raise RuntimeError('Validator for immediate task must be either a boolean or a callback(data).')

    def can_still_process(self):
        """ Return True if this immediate task can still be processed for the first time.
            If False is returned, task is drop and never processed (not even for a first time).
        """
        return self.validator()

    def update_delay(self, new_delay):
        self.deadline.start_time = -new_delay
        self.deadline.delay = new_delay

class Scheduler:
    """ (public) Scheduler class. """
    __slots__ = ['unit', 'current_time', 'callback_process', 'data_in_queue', 'data_in_heap', 'tasks_queue', 'lock']

    def __init__(self, unit_in_seconds, callback_process):
        """ Initialize a scheduler.

            :param unit_in_seconds: number of seconds to wait for each step.
            :param callback_process: callback to call on every task.

                - Signature: ``task_callback(task.data) -> bool``
                - If callback return True, task is considered done and is removed from scheduler.
                - Otherwise, task is rescheduled for another delay.
        """
        assert isinstance(unit_in_seconds, int) and unit_in_seconds > 0
        assert callable(callback_process)
        self.unit = unit_in_seconds
        self.current_time = 0
        self.callback_process = callback_process
        self.data_in_heap = PriorityDict()  # data => Deadline
        self.data_in_queue = {}  # type: dict{object, _Task}  # data => associated Task in queue
        self.tasks_queue = Queue()
        # Lock to modify this object safely inside one Tornado thread:
        # http://www.tornadoweb.org/en/stable/locks.html
        self.lock = Lock()

    def _enqueue(self, task):
        """ Put a task in queue of tasks to process now. """
        self.data_in_queue[task.data] = task
        self.tasks_queue.put_nowait(task)

    @gen.coroutine
    def has_data(self, data):
        """ Return True if given data is associated to any task. """
        with (yield self.lock.acquire()):
            return data in self.data_in_heap or data in self.data_in_queue

    @gen.coroutine
    def get_info(self, data):
        """ Return info about scheduling for given data, or None if data is not found. """
        with (yield self.lock.acquire()):
            deadline = None  # type: _Deadline
            if data in self.data_in_heap:
                deadline = self.data_in_heap[data]
            if data in self.data_in_queue:
                deadline = self.data_in_queue[data].deadline
            if deadline:
                return SchedulerEvent(time_unit=self.unit,
                                      time_added=deadline.start_time,
                                      delay=deadline.delay,
                                      current_time=self.current_time)
        return None

    @gen.coroutine
    def add_data(self, data, nb_units_to_wait):
        """ Add data with a non-null deadline. For null deadlines, use no_wait().

            :param data: data to add
            :param nb_units_to_wait: time to wait (in number of units)
        """
        if not isinstance(nb_units_to_wait, int) or nb_units_to_wait <= 0:
            raise exceptions.NaturalIntegerNotNullException()
        with (yield self.lock.acquire()):
            if data in self.data_in_heap or data in self.data_in_queue:
                raise exceptions.AlreadyScheduledException()
            # Add task to scheduler.
            self.data_in_heap[data] = _Deadline(self.current_time, nb_units_to_wait)

    @gen.coroutine
    def no_wait(self, data, nb_units_to_wait, processing_validator):
        """ Add a data to be processed the sooner.

            :param data: data to add
            :param nb_units_to_wait: time to wait (in number of units) for data tasks after first task is executed.
                If null (0), data is processed once (first time) and then dropped.
            :param processing_validator: validator used to check if data can still be processed for the first time.
                See documentation of class _ImmediateTask for more details.
        """
        if not isinstance(nb_units_to_wait, int) or nb_units_to_wait < 0:
            raise exceptions.NaturalIntegerException()
        with (yield self.lock.acquire()):
            if data in self.data_in_heap:
                # Move data from heap to queue with new delay.
                del self.data_in_heap[data]
                self._enqueue(_ImmediateTask(data, nb_units_to_wait, processing_validator))
            elif data in self.data_in_queue:
                # Change delay for future scheduling.
                self.data_in_queue[data].update_delay(nb_units_to_wait)
            else:
                # Add data to queue.
                self._enqueue(_ImmediateTask(data, nb_units_to_wait, processing_validator))

    @gen.coroutine
    def remove_data(self, data):
        """ Remove a data (and all associated tasks) from scheduler. """
        with (yield self.lock.acquire()):
            if data in self.data_in_heap:
                del self.data_in_heap[data]
            elif data in self.data_in_queue:
                # Remove task from data_in_queue and invalidate it in queue.
                self.data_in_queue.pop(data).valid = False

    @gen.coroutine
    def _step(self):
        """ Compute a step (check and enqueue tasks to run now) in scheduler. """
        with (yield self.lock.acquire()):
            self.current_time += 1
            while self.data_in_heap:
                deadline, data = self.data_in_heap.smallest()
                if deadline.deadline > self.current_time:
                    break
                del self.data_in_heap[data]
                self._enqueue(_Task(data, deadline))

    @gen.coroutine
    def schedule(self):
        """ Main scheduler method (callback to register in ioloop). Wait for unit seconds and
            run tasks after each wait time.
        """
        while True:
            yield gen.sleep(self.unit)
            yield self._step()

    @gen.coroutine
    def process_tasks(self):
        """ Main task processing method (callback to register in ioloop). Consume and process tasks in queue
            and reschedule processed tasks when relevant.

            A task is processed if associated data was not removed from scheduler.

            A task is rescheduled if processing callback returns False
            (True means `task definitively done`) AND if task deadline is not null.
        """
        while True:
            task = yield self.tasks_queue.get()  # type: _Task
            try:
                if task.valid and (not isinstance(task, _ImmediateTask) or task.can_still_process()):
                    if gen.is_coroutine_function(self.callback_process):
                        remove_data = yield self.callback_process(task.data)
                    else:
                        remove_data = self.callback_process(task.data)
                    remove_data = remove_data or not task.deadline.delay
                    with (yield self.lock.acquire()):
                        del self.data_in_queue[task.data]
                        if not remove_data:
                            self.data_in_heap[task.data] = _Deadline(self.current_time, task.deadline.delay)
            finally:
                self.tasks_queue.task_done()
