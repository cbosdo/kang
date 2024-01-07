import pytest
import time
import os

import kang.scheduler

def start():
    '''
    Fake start function to test the scheduler
    '''

def stop():
    '''
    Fake stop function to test the scheduler
    '''

EVENTS_FILE = "events.txt"

EVENTS_DATA = '''1706514300.0,10,start,[1],{"foo": "bar"}
1706517900.0,10,stop,[1],{"foo": "bar"}
'''

@pytest.fixture
def make_persisted_scheduler():
    """
    Convenience fixture to easily create a scheduler with data
    """
    def _make_scheduler(data):

        with open(EVENTS_FILE, "w") as fd:
            fd.write(data)

        scheduler = kang.scheduler.PersistedScheduler(EVENTS_FILE, [start, stop])
        return scheduler

    yield _make_scheduler
    os.remove(EVENTS_FILE)

def assert_event_file(expected):
    '''
    Assert that the events file contains the expected data
    '''
    with open(EVENTS_FILE, "r") as fd:
        actual = fd.read()

    assert actual == expected


def test_persisted_scheduler_load(make_persisted_scheduler):
    '''
    Test the scheduler thread
    '''
    scheduler = make_persisted_scheduler(EVENTS_DATA)
    loaded_events = scheduler.events

    assert len(loaded_events) == 2
    assert loaded_events[0].time == 1706514300.0
    assert loaded_events[0].priority == 10
    assert loaded_events[0].action == start
    assert loaded_events[0].argument == (1,)
    assert loaded_events[0].kwargs == {"foo": "bar"}

    assert loaded_events[1].time == 1706517900.0
    assert loaded_events[1].priority == 10
    assert loaded_events[1].action == stop
    assert loaded_events[1].argument == (1,)
    assert loaded_events[1].kwargs == {"foo": "bar"}


def test_persisted_scheduler_save(make_persisted_scheduler):
    '''
    Test saving events in the scheduler
    '''
    scheduler = make_persisted_scheduler("")
    scheduler.enterabs(1706514300.0, 10, start, (1,), {"foo": "bar"})
    scheduler.enterabs(1706517900.0, 10, stop, (1,), {"foo": "bar"})

    assert_event_file(EVENTS_DATA)


def test_persisted_scheduler_cancel(make_persisted_scheduler):
    '''
    Test the scheduler thread
    '''
    scheduler = make_persisted_scheduler(EVENTS_DATA)

    for event in scheduler.events:
        scheduler.cancel(event)

    assert len(scheduler.events) == 0
    assert_event_file("")
