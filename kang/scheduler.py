import json
import os.path
import sched
import threading
import time
from collections import namedtuple


def _persisted_action(action, argument, kwargs, saver):
    action(*argument, **kwargs)
    saver()


class PersistedScheduler(sched.scheduler):
    def __init__(self, path, functions):
        """
        Create a new persisted scheduler instance.

        If the passed path exists, the events contained in it will be loaded in
        the new instance.

        :param path: the path to the file where the events queue is persisted.
        :param functions: list of functions to be used as actions
        """
        sched.scheduler.__init__(self, time.time, time.sleep)
        func_map = {func.__name__: func for func in functions}
        self.path = path
        if os.path.isfile(path):
            # Load the persisted events
            with open(self.path, "r") as fd:
                events = [line.strip().split(",") for line in fd.readlines()]
                for event in events:
                    if len(event) != 5:
                        continue
                    func = func_map[event[2]]
                    self.enterabs(
                        float(event[0]),
                        int(event[1]),
                        func,
                        argument=json.loads(event[3]),
                        kwargs=json.loads(event[4]),
                    )

    def enterabs(self, time, priority, action, argument=(), kwargs={}):
        """
        Enter a persisted event in the scheduler. The queue is automatically saved after entering the event,
        but also after the event has been run.
        """
        event = sched.scheduler.enterabs(
            self,
            time,
            priority,
            _persisted_action,
            argument=(action, argument, kwargs, self.save),
        )
        self.save()
        return event

    def enter(self, delay, priority, action, argument=(), kwargs={}):
        """
        Enter a persisted event in the scheduler. The queue is automatically saved after entering the event,
        but also after the event has been run.
        """
        event = sched.scheduler.enterabs(
            self,
            time.time() + delay,
            priority,
            _persisted_action,
            argument=(action, argument, kwargs, self.save),
        )
        self.save()
        return event

    def cancel(self, event):
        """
        Cancel a persisted event from the scheduler. Raises ValueError if the event isn't queued.
        """
        for persisted_event in self.queue:
            if persisted_event.time == event.time and \
               persisted_event.priority == event.priority and \
               persisted_event.argument[0] == event.action and \
               persisted_event.argument[1] == event.argument and \
               persisted_event.argument[2] == event.kwargs:
                sched.scheduler.cancel(self, persisted_event)
                self.save()
                break

    @property
    def events(self):
        """
        Return the list of scheduled events
        """
        Event = namedtuple(
            "Event", ["time", "priority", "action", "argument", "kwargs"]
        )
        return [
            Event(
                event.time,
                event.priority,
                event.argument[0],
                event.argument[1],
                event.argument[2],
            )
            for event in self.queue
        ]

    def save(self):
        """
        Persist the scheduled events to a file
        """
        if not self.path:
            print("No path")
            return
        with open(self.path, "w") as fd:
            for event in self.events:
                action = event.action
                argument = event.argument
                kwargs = event.kwargs
                fd.write(
                    "{},{},{},{},{}\n".format(
                        event.time,
                        event.priority,
                        action.__name__,
                        json.dumps(argument),
                        json.dumps(kwargs),
                    )
                )


class SchedulerThread(threading.Thread):
    """
    Thread handling a persisted scheduler.
    """

    def __init__(self, path, functions):
        """
        Create a new threaded persisted scheduler instance.

        :param path: the path to the file where the events queue is persisted.
        :param functions: list of functions to be used as actions
        """
        super().__init__(name="Scheduler Thread")
        self.scheduler = PersistedScheduler(path, functions)
        self.stopping = False
        self.lock = threading.Lock()

    def enterabs(self, time, priority, action, argument=(), kwargs={}):
        """
        Enter a persisted event in the scheduler. The queue is automatically saved after entering the event,
        but also after the event has been run.
        """
        self.lock.acquire()
        event = self.scheduler.enterabs(time, priority, action, argument, kwargs)
        self.lock.release()
        return event

    def enter(self, delay, priority, action, argument=(), kwargs={}):
        """
        Enter a persisted event in the scheduler. The queue is automatically saved after entering the event,
        but also after the event has been run.
        """
        self.lock.acquire()
        event = self.scheduler.enter(delay, priority, action, argument, kwargs)
        self.lock.release()
        return event

    def empty(self):
        """
        Thread safe function checking if the scheduler queue is empty
        """
        self.lock.acquire()
        result = self.scheduler.empty()
        self.lock.release()
        return result

    @property
    def events(self):
        """
        Return the queue of events
        """
        self.lock.acquire()
        result = None
        try:
            result = self.scheduler.events
        finally:
            self.lock.release()
        return result

    def cancel(self, time, action, argument=(), kwargs={}):
        """
        Cancel an action from the queue in a thread-safe way.

        :param time: time of the action to cancel
        :param action: function of the action to cancel
        :param argument: positional arguments of the action to cancel
        :param kwargs: named arguments of the action to cancel

        Raises ValueError if not matching event can be found in the queue
        """
        self.lock.acquire()
        found = False
        for event in self.scheduler.events:
            if (
                event.time == time
                and event.action == action
                and event.argument == argument
                and event.kwargs == kwargs
            ):
                found = event
                break
        if not found:
            self.lock.release()
            raise ValueError()
        self.scheduler.cancel(found)
        self.lock.release()

    def stop(self):
        """
        Call to stop the scheduler thread.
        """
        self.stopping = True

    def run(self):
        while not self.stopping:
            self.lock.acquire()
            if not self.scheduler.empty():
                self.scheduler.run(blocking=False)
            self.lock.release()
            time.sleep(1)
