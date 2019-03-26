import json
import os
from glob import glob

P = '/tmp/dings/'

prefixes = list(set(p[:8] for p in os.listdir(P)))

# assume a file 'migrating.txt' with lines of the full package path of objects to migrate, e.g.
# raiden.transfer.state.NettingChannelState
# raiden.transfer.events.ContractSendChannelClose
# ...
with open('migrating.txt') as f:
    migrating = [m.strip() for m in f.readlines()]


def prefix_iterator():
    for prefix in prefixes:
        text = ''
        for fn in glob(os.path.join(P, prefix + '*')):
            with open(fn) as f:
                text += f.read()
        yield prefix, text


def counts(text):
    match = 0
    misses = []
    for migration in migrating:
        if migration in text:
            match += 1
        else:
            misses.append(migration)
    return (float(match) / len(migrating)), misses


if __name__ == '__main__':
    matches = []
    for prefix, text in prefix_iterator():
        matches.append((prefix, counts(text)))
    print(
        json.dumps(
            sorted(matches, key=lambda e: e[1][0]),
            indent=2,
        ),
    )
