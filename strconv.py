# Copyright (c) 2013-2018 Byron Ruth
# BSD License

import re
import sys
from collections import Counter
from datetime import datetime

__version__ = '0.5'


class TypeInfo(object):
    """Sampling and frequency of a type for a sample of values."""

    def __init__(self, name, size=None, total=None):
        self.name = name
        self.count = 0
        self.sample = []
        self.size = size
        self.total = total
        self.sample_set = set()

    def __repr__(self):
        return '<{0}: {1} n={2}>'.format(self.__class__.__name__,
                                         self.name, self.count)

    def incr(self, n=1):
        self.count += n

    def add(self, i, value):
        if self.size is None or len(self.sample) < self.size:
            # No dupes
            if value not in self.sample_set:
                self.sample_set.add(value)
                self.sample.append((i, value))

    def freq(self):
        if self.total:
            return self.count / float(self.total)
        return 0.


class Types(object):
    """Type information for a sample of values."""

    def __init__(self, size=None, ignore_nulls=True):
        self.size = size
        self.total = None
        self.types = {}
        self.ignore_nulls = ignore_nulls

    def __repr__(self):
        if self.ignore_nulls:
            types = self.inferred_col_type()
        else:
            types = self.most_common()
        label = ', '.join(['{0}={1}'.format(t, i) for t, i in types])
        return '<{0}: {1}>'.format(self.__class__.__name__, label)

    def incr(self, t, n=1):
        if t is None:
            t = 'string'
        if t not in self.types:
            self.types[t] = TypeInfo(t, self.size, self.total)
        self.types[t].incr(n)

    def add(self, t, i, value):
        if t is None:
            t = 'string'
        if t not in self.types:
            self.types[t] = TypeInfo(t, self.size, self.total)
        self.types[t].add(i, value)

    def set_total(self, total):
        self.total = total
        for k in self.types:
            self.types[k].total = total

    def most_common(self, n=None):
        if n is None:
            n = len(self.types)
        c = Counter()
        for t in self.types:
            c[t] = self.types[t].count
        return c.most_common(n)

    def inferred_col_type(self):
        c = Counter()
        for t in self.types:
            c[t] = self.types[t].count
        if c.most_common()[0][0] == 'none':
            try:
                if c.most_common()[1][0] == 'int' and 'float' in c:
                    return [('float', c['float'])]
                return [c.most_common()[1]]
            except IndexError:
                return [('empty', c.most_common()[0][1])]

        if c.most_common()[0][0] == 'int' and 'float' in c:
            return [('float', c['float'])]
        return [c.most_common(1)[0]]


class Strconv(object):
    def __init__(self, converters=()):
        self.converters = {}
        self._order = []

        for name, func in converters:
            self.converters[name] = func
            self._order.append(name)

    def register_converter(self, name, func, priority=None):
        if name is None:
            raise ValueError('type name cannot be None')
        if not callable(func):
            raise ValueError('converter functions must be callable')

        self.converters[name] = func

        if name in self._order:
            self._order.remove(name)

        if priority is not None and priority < len(self._order):
            self._order.insert(priority, name)
        else:
            self._order.append(name)

    def unregister_converter(self, name):
        if name in self._order:
            self._order.remove(name)
        if name in self.converters:
            del self.converters[name]

    def get_converter(self, name):
        if name not in self.converters:
            raise KeyError('no converter for type "{0}"'.format(name))
        return self.converters[name]

    def convert(self, s, include_type=False):
        if s is None or s == '':
            s = 'None'
        if isinstance(s, str):
            for t in self._order:
                func = self.converters[t]
                try:
                    v = func(s)
                    if include_type:
                        return v, t
                    return v
                except ValueError:
                    pass
        if include_type:
            return s, None
        return s

    def convert_series(self, iterable, include_type=False):
        for s in iterable:
            yield self.convert(s, include_type=include_type)

    def convert_matrix(self, matrix, include_type=False):
        for r in matrix:
            yield tuple(self.convert(s, include_type=include_type) for s in r)

    def infer(self, s, converted=False):
        v, t = self.convert(s, include_type=True)
        if t and converted:
            return type(v)
        return t

    def infer_series(self, iterable, n=None, size=10):
        info = Types(size=size)
        i = -1

        for i, value in enumerate(iterable):
            if n and i >= n:
                break

            t = self.infer(value)
            info.incr(t)
            info.add(t, i, value)

        i += 1

        # No reason to return type info when no data exists
        if i == 0:
            return

        info.set_total(i)
        return info

    def infer_matrix(self, matrix, n=None, size=10):
        infos = []
        i = -1

        for i, iterable in enumerate(matrix):
            if n and i >= n:
                break

            for j, value in enumerate(iterable):
                if i == 0:
                    infos.append(Types(size=size))
                info = infos[j]

                t = self.infer(value)
                info.incr(t)
                info.add(t, i, value)

        i += 1

        for info in infos:
            info.set_total(i)

        return infos


# Built-in converters

# Use dateutil for more robust parsing
try:
    from dateutil.parser import parse as duparse
except ImportError:
    import warnings
    warnings.warn('python-dateutil is not installed. As of version 0.5, '
                  'this will be a hard dependency of strconv for'
                  'datetime parsing. Without it, only a limited set of '
                  'datetime formats are supported without timezones.')
    duparse = None

CORE_DATE_FORMATS = (
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%d-%m-%y',
    '%d.%m.%Y',
    '%Y/%m/%d',
    '%d/%m/%Y',
)

DATE_FORMATS = (
    *CORE_DATE_FORMATS,
    '%d %B, %Y',
    '%d %B, %y',
    '%d %b, %Y',
    '%d %b, %y',
    '%B %d, %Y',
    '%b %d, %Y',
)

TIME_FORMATS = (
    '%H:%M:%S',
    '%H:%M',
    '%I:%M:%S %p',
    '%I:%M:%S %z',
    '%I:%M %p',
    '%I:%M %z',
    '%I:%M',
)

DATE_TIME_SEPS = (' ', 'T')

true_re = re.compile(r'^(t(rue)?|yes)$', re.I)
false_re = re.compile(r'^(f(alse)?|no)$', re.I)


def convert_none(s):
    if s is None or s == 'None' or s == '':
        return None
    raise ValueError


def convert_int(s):
    return int(s)


def convert_float(s):
    return float(s)


def convert_bool(s):
    if true_re.match(s):
        return True
    if false_re.match(s):
        return False
    raise ValueError


def convert_datetime(s, date_formats=DATE_FORMATS, time_formats=TIME_FORMATS):
    if sys.version < '3.5':
        if duparse:
            try:
                dt = duparse(s)
                if dt.time():
                    return duparse(s)
            except TypeError:  # parse may throw this in py3
                raise ValueError

    for df in date_formats:
        for tf in time_formats:
            for sep in DATE_TIME_SEPS:
                f = '{0}{1}{2}'.format(df, sep, tf)
                try:
                    return datetime.strptime(s, f)
                except ValueError:
                    pass
    raise ValueError


def convert_date(s, date_formats=DATE_FORMATS):
    if duparse:
        try:
            return duparse(s).date()
        except TypeError:  # parse may throw this in py3
            raise ValueError

    for f in date_formats:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError


def convert_time(s, time_formats=TIME_FORMATS):
    for f in time_formats:
        try:
            return datetime.strptime(s, f).time()
        except ValueError:
            pass
    raise ValueError


# Initialize default instance and make accessible at the module level
# Note: Order matters!
default_strconv = Strconv(converters=[
    ('none', convert_none),
    ('int', convert_int),
    ('float', convert_float),
    ('bool', convert_bool),
    ('time', convert_time),
    ('datetime', convert_datetime),
    ('date', convert_date),
])

register_converter = default_strconv.register_converter
unregister_converter = default_strconv.unregister_converter
get_converter = default_strconv.get_converter

convert = default_strconv.convert
convert_series = default_strconv.convert_series
convert_matrix = default_strconv.convert_matrix

infer = default_strconv.infer
infer_series = default_strconv.infer_series
infer_matrix = default_strconv.infer_matrix
