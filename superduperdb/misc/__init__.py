import superduperdb as s

if s.CFG.debug:
    from . import _time as time
else:
    import time

__all__ = 'time',
