#!/usr/bin/env python

import unittest
import strconv
from datetime import datetime, date, time
from dateutil.tz import tzoffset


class StrconvTestCase(unittest.TestCase):
    def setUp(self):
        self.s = strconv.Strconv()

    def test_default(self):
        self.assertEqual(len(self.s.converters), 0)
        self.assertRaises(KeyError, self.s.get_converter, 'int')
        self.assertEqual(self.s.convert('1'), '1')

    def test_register(self):
        self.s.register_converter('int', strconv.convert_int)
        self.assertEqual(len(self.s.converters), 1)
        self.assertEqual(self.s.convert('1'), 1)
        self.assertEqual(self.s.get_converter('int'), strconv.convert_int)

    def test_unregister(self):
        self.s.register_converter('int', strconv.convert_int)
        self.s.unregister_converter('int')
        self.assertEqual(len(self.s.converters), 0)
        self.assertEqual(self.s.convert('1'), '1')

    def test_register_priority(self):
        self.s.register_converter('int', strconv.convert_int)
        self.s.register_converter('bool', strconv.convert_bool, priority=0)
        self.assertEqual(self.s._order, ['bool', 'int'])

    def test_register_none(self):
        self.assertRaises(ValueError, self.s.register_converter,
                          None, lambda x: x)
        self.assertRaises(ValueError, self.s.register_converter,
                          'name', None)


class ConvertTestCase(unittest.TestCase):
    def test_convert(self):
        self.assertEqual(strconv.convert('-3'), -3)
        self.assertEqual(strconv.convert('+0.4'), 0.4)
        self.assertEqual(strconv.convert('true'), True)
        self.assertEqual(strconv.convert('3/20/2013'), date(2013, 3, 20))
        self.assertEqual(strconv.convert('5:40 PM'), time(17, 40))
        self.assertEqual(strconv.convert('March 4, 2013 5:40 PM'),
                         datetime(2013, 3, 4, 17, 40, 0))
        self.assertEqual(strconv.convert('March 4, 2013 12:00 AM'),
                         datetime(2013, 3, 4, 0, 0))

    def test_convert_include_type(self):
        self.assertEqual(strconv.convert('-3', include_type=True), (-3, 'int'))

    def test_convert_series(self):
        self.assertEqual(list(strconv.convert_series(['+0.4'])), [0.4])

    def test_convert_matrix(self):
        self.assertEqual(list(strconv.convert_matrix([['+0.4']])), [(0.4,)])


class InferTestCase(unittest.TestCase):
    def test_infer(self):
        self.assertEqual(strconv.infer(''), 'none')
        self.assertEqual(strconv.infer('None'), 'none')
        self.assertEqual(strconv.infer(None), 'none')
        self.assertEqual(strconv.infer('-3'), 'int')
        self.assertEqual(strconv.infer('+0.4'), 'float')
        self.assertEqual(strconv.infer('true'), 'bool')
        self.assertEqual(strconv.infer('3/20/2013'), 'date')
        self.assertEqual(strconv.infer('5:40 PM'), 'time')
        self.assertEqual(strconv.infer('March 4, 2013 5:40 PM'), 'datetime')
        self.assertEqual(strconv.infer('2018-12-01 00:00:00'), 'datetime')
        self.assertEqual(strconv.infer('March 4, 2013 12:00 PM'), 'datetime')
        # Midnight
        self.assertEqual(strconv.convert_datetime('2013-03-01 00:00:00'),
                         datetime(2013, 3, 1, 0, 0, 0))
        self.assertEqual(strconv.convert_datetime('2018/03/01 00:00:00'),
                         datetime(2018, 3, 1, 0, 0, 0))

    def test_infer_converted(self):
        self.assertEqual(strconv.infer('', converted=True), type(None))
        self.assertEqual(strconv.infer('None', converted=True), type(None))
        self.assertEqual(strconv.infer(None, converted=True), type(None))
        self.assertEqual(strconv.infer('-3', converted=True), int)
        self.assertEqual(strconv.infer('+0.4', converted=True), float)
        self.assertEqual(strconv.infer('true', converted=True), bool)
        self.assertEqual(strconv.infer('3/20/2013', converted=True), date)
        self.assertEqual(strconv.infer('5:40 PM', converted=True), time)
        self.assertEqual(strconv.infer('March 4, 2013 5:40 PM',
                         converted=True), datetime)

    def test_infer_series(self):
        c0 = strconv.infer_series(['+0.4', '1.0', '0.', 'None'])
        c1 = strconv.infer_series(['', 'None', None])
        self.assertEqual(c0.most_common(), [('float', 3), ('none', 1)])
        self.assertEqual(c0.types['float'].freq(), 0.75)
        self.assertEqual(c0.types['float'].count, 3)
        self.assertEqual(c0.types['float'].size, 10)  # default size
        self.assertEqual(c1.types['none'].count, 3)
        self.assertEqual(c1.types['none'].freq(), 1.0)
        self.assertEqual(c1.types['none'].size, 10)
        self.assertEqual(c1.inferred_col_type(), [('empty', 3)])

        self.assertEqual(strconv.infer_series([]), None)

    def test_infer_series_n(self):
        c0 = strconv.infer_series(['+0.4', '1.0', '0.', 'None'], n=1)
        c1 = strconv.infer_series(['+0.4', '1.0', '0.', 'None'], n=2)
        c2 = strconv.infer_series(['', 'None', None], n=2)
        c3 = strconv.infer_series(['', 'None', None], n=3)
        self.assertEqual(c0.most_common(), [('float', 1)])
        self.assertEqual(c0.types['float'].count, 1)
        self.assertEqual(c1.most_common(), [('float', 2)])
        self.assertEqual(c0.inferred_col_type(), [('float', 1)])
        self.assertEqual(c1.inferred_col_type(), [('float', 2)])
        self.assertEqual(c2.inferred_col_type(), [('empty', 2)])
        self.assertEqual(c3.inferred_col_type(), [('empty', 3)])

    def test_infer_matrix(self):
        c0, c1, c2, c3, c4, c5, c6, c7 = strconv.infer_matrix([
            ['+0.4',    'true', '50', None,       '1/1/2000', 'None',       None,   None],
            ['1',       'true', '50', None,       '1/1/2000', 'None',       None,   None],
            ['1',       'true', '50', None,       '1/1/2000', 'None',       None,   '14.3'],
            ['1',       'true', '50', '1/1/2000', None,       '1/1/2000',   None,   '100']])
        self.assertEqual(c0.most_common(n=1), [('int', 3)])
        self.assertEqual(c0.types['float'].freq(), 0.25)
        self.assertEqual(c0.size, 10)  # default size
        self.assertEqual(c0.inferred_col_type(), [('float', 1)])
        self.assertEqual(c3.most_common(n=1), [('none', 3)])
        self.assertEqual(c4.most_common(n=1), [('date', 3)])
        self.assertEqual(c3.inferred_col_type(), [('date', 1)])
        self.assertEqual(c4.inferred_col_type(), [('date', 3)])
        self.assertEqual(c5.most_common(n=1), [('none', 3)])
        self.assertEqual(c5.inferred_col_type(), [('date', 1)])
        self.assertEqual(c6.most_common(n=1), [('none', 4)])
        self.assertEqual(c6.inferred_col_type(), [('empty', 4)])
        self.assertEqual(c7.inferred_col_type(), [('float', 1)])

        self.assertEqual(strconv.infer_matrix([]), [])

    def test_infer_matrix_n(self):
        c0, c1, c2, c3, c4 = strconv.infer_matrix([
            ['+0.4', 'true', '50', None, ''],
            ['+0.3', 'f', '0', '4', ''],
        ], n=1)
        self.assertEqual(c0.most_common(), [('float', 1)])
        self.assertEqual(c1.most_common(), [('bool', 1)])
        self.assertEqual(c2.most_common(), [('int', 1)])
        self.assertEqual(c3.most_common(), [('none', 1)])
        self.assertEqual(c4.most_common(), [('none', 1)])


class ConverterTestCase(unittest.TestCase):
    def test_convert_none(self):
        self.assertEqual(strconv.convert_none(''), None)
        self.assertEqual(strconv.convert_none('None'), None)
        self.assertEqual(strconv.convert_none(None), None)

    def test_convert_int(self):
        self.assertEqual(strconv.convert_int('0'), 0)
        self.assertEqual(strconv.convert_int('1'), 1)
        self.assertEqual(strconv.convert_int('+1'), 1)
        self.assertEqual(strconv.convert_int('-1'), -1)

    def test_convert_float(self):
        self.assertEqual(strconv.convert_float('0.'), 0.0)
        self.assertEqual(strconv.convert_float('+.0'), 0.0)
        self.assertEqual(strconv.convert_float('-.0'), 0.0)
        self.assertEqual(strconv.convert_float('1.'), 1.0)
        self.assertEqual(strconv.convert_float('+1.'), 1.0)
        self.assertEqual(strconv.convert_float('-1.'), -1.0)

    def test_convert_bool(self):
        self.assertEqual(strconv.convert_bool('t'), True)
        self.assertEqual(strconv.convert_bool('true'), True)
        self.assertEqual(strconv.convert_bool('yes'), True)
        self.assertEqual(strconv.convert_bool('f'), False)
        self.assertEqual(strconv.convert_bool('false'), False)
        self.assertEqual(strconv.convert_bool('no'), False)

    def test_convert_date(self):
        self.assertEqual(strconv.convert_date('2013-03-01'), date(2013, 3, 1))
        self.assertEqual(strconv.convert_date('2013-3-1'), date(2013, 3, 1))
        self.assertEqual(strconv.convert_date('3-1-2013'), date(2013, 3, 1))
        self.assertEqual(strconv.convert_date('3/1/2013'), date(2013, 3, 1))
        self.assertEqual(strconv.convert_date('3.1.2013'), date(2013, 3, 1))
        self.assertEqual(strconv.convert_date('Mar 1, 2013'), date(2013, 3, 1))
        self.assertEqual(strconv.convert_date('31/12/2022'), date(2022, 12, 31))
        self.assertEqual(strconv.convert_date('2022/12/31'), date(2022, 12, 31))

    def test_convert_time(self):
        self.assertEqual(strconv.convert_time('01:30'), time(1, 30, 0))
        self.assertEqual(strconv.convert_time('1:30'), time(1, 30, 0))
        self.assertEqual(strconv.convert_time('1:30:40'), time(1, 30, 40))
        self.assertEqual(strconv.convert_time('1:30:40 pm'), time(13, 30, 40))
        self.assertEqual(strconv.convert_time('15:30:40'), time(15, 30, 40))
        self.assertEqual(strconv.convert_time('5:30:40 AM'), time(5, 30, 40))

    def test_convert_datetime(self):
        tzoff = tzoffset(None, -18000)

        self.assertEqual(strconv.convert_datetime('Mar 1, 2013T5:30:40 AM'),
                         datetime(2013, 3, 1, 5, 30, 40))
        self.assertEqual(strconv.convert_datetime('Mar 1, 2013 5:30:40 AM'),
                         datetime(2013, 3, 1, 5, 30, 40))
        self.assertRaises(ValueError, strconv.convert_datetime, 'foo')

        # TZ
        self.assertEqual(strconv.convert_datetime('2013-03-01 5:30:40 -0500'),
                         datetime(2013, 3, 1, 5, 30, 40, tzinfo=tzoff))


if __name__ == '__main__':
    unittest.main()
