import gc
import json
import os
import tempfile
from functools import partial
from itertools import chain, combinations, product
from sqlite3 import ProgrammingError

import gevent
from eth_utils import to_checksum_address


def cleanup_tasks():
    tasks = [
        running_task
        for running_task in gc.get_objects()
        if isinstance(running_task, gevent.Greenlet)
    ]
    gevent.killall(tasks)
    gevent.hub.reinit()


DB_DUMP_PATH = '/tmp/dings/'


def shutdown_apps_and_cleanup_tasks(raiden_apps, name):

    def fix(data):
        """Fix double json encoding of `*Record.data` fields."""
        assert isinstance(data, list)
        fixed = []
        for record in data:
            if isinstance(record, tuple):
                new_record = tuple()
                record_data = record.data
                for v in record:
                    if v == record_data:
                        new_record += (json.loads(record.data), )
                    else:
                        new_record += (v, )
                fixed.append(new_record)
            elif isinstance(record, str) and record.startswith('{'):
                fixed.append(json.loads(record))
            else:
                fixed.append(record)
        return fixed

    def flat(it):
        return [item for sublist in it for item in sublist]

    for num, app in enumerate(raiden_apps):
        address = to_checksum_address(app.raiden.address)
        batch = 500
        tmppath = tempfile.mktemp(prefix=DB_DUMP_PATH, suffix=name + str(num))
        for kind, call in (
                (
                    'events',
                    partial(app.raiden.wal.storage.batch_query_event_records, batch),
                ),
                (
                    'state_changes',
                    partial(app.raiden.wal.storage.batch_query_state_changes, batch),
                ),
                (
                    'snapshots',
                    app.raiden.wal.storage.get_snapshots,
                ),
        ):
            fn = f'{tmppath}-{kind}-{address}.json'
            try:
                with open(fn, 'w', encoding='utf-8') as f:
                    dump = fix(flat(call()))
                    json.dump(dump, f, indent=2)
            except ProgrammingError as e:
                print(e)
                assert tmppath.startswith(DB_DUMP_PATH)
                assert tmppath.startswith('/tmp')
                assert len(tmppath) > len(DB_DUMP_PATH)
                os.remove(fn)
        app.stop()

    # Two tests in sequence could run a UDP server on the same port, a hanging
    # greenlet from the previous tests could send packet to the new server and
    # mess things up. Kill all greenlets to make sure that no left-over state
    # from a previous test interferes with a new one.
    cleanup_tasks()


def all_combinations(values):
    """ Returns all possible combinations, from length 1 up to full-length of
    values.
    """
    all_generators = (
        combinations(values, r)
        for r in range(1, len(values))
    )
    flat = chain.from_iterable(all_generators)
    return flat


def fixture_all_combinations(invalid_values):
    """ Generate all combinations for testing invalid values.

    `pytest.mark.parametrize` will generate the combination of the full-length
    values, this is not sufficient for an exhaustive failing test with default
    values, example::

        @pytest.mark.parametrize('x', [0, 1])
        @pytest.mark.parametrize('y', [2, 3])
        def test_foo(x, y):
            with pytest.raises(Exception):
                # failing computation with x and y

    The above test will generate 4 tests {x:0,y:2}, {x:0,y:3}, {x:1,y:2}, and
    {x:1,y:3}, but it will not generate a scenario for x and y alone {x:0},
    {x:1}, {y:2}, {y:3}.
    """
    # all_combinations needs an object with length
    invalid_values_items = list(invalid_values.items())

    # Generate all possible test combinations. E.g. `{a: [..], b: [..]}` will
    # produce tests for:
    # - `{a: [..]}`
    # - `{b: [..]}`
    # - `{a: [..], b: [..]}`
    all_invalid_values = all_combinations(invalid_values_items)

    # Expand the generate test. E.g. {a: [1,2], b:[3,4]} will produce:
    # - {a: 1, b:3}
    # - {a: 1, b:4}
    # - {a: 2, b:3}
    # - {a: 2, b:4}
    for invalid_combinations in all_invalid_values:
        # expand the value list `(key, [v1,v2])` to `((key, v1), (key, v2))`
        keys_values = (
            product((key,), values)
            for key, values in invalid_combinations
        )

        # now make the cartesian product of all possible invalid keys and values
        invalid_instances = product(*keys_values)

        for instance in invalid_instances:
            yield dict(instance)
