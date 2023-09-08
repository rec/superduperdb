import re

import superduperdb as s

CODE_ROOTS = s.ROOT / 'superduperdb', s.ROOT / 'test'

# DEFECTS maps defect names to functions that match a defect in a line of code.
# The last two patterns match their own definitions :-D so 1 is the lowest possible
# defect count for them.

DEFECTS = {
    'assert_isinstance': 'assert isinstance\(',
    'cast': r't\.cast\(',
    'noqa': r'# .*noqa: ',
    'type_ignore': r'# .*type: ignore',
}

# ALLOWABLE_DEFECTS has the allowable defect counts, which should be NON-INCREASING
# over time.  If you have decreased the number of defects, change it here,
# and take a bow!
ALLOWABLE_DEFECTS = {
    'assert_isinstance': 48,  # Try to keep this down
    'cast': 13,  # Try to keep this down
    'noqa': 1,  # This should never change
    'type_ignore': 36,  # This should only ever increase in obscure edge cases
}


def test_quality():
    files = (f for root in CODE_ROOTS for f in sorted(root.glob('**/*.py')))
    lines = [line for f in files for line in f.read_text().splitlines()]
    searches = ((k, re.compile(v).search) for k, v in DEFECTS.items())
    defects = {k: sum(bool(v(line)) for line in lines) for k, v in searches}

    assert defects == ALLOWABLE_DEFECTS
    assert defects['noqa'] == 1, 'There is never a need for noqa: fix your code'
