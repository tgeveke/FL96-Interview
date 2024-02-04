import unittest
import FL96

class CSVTests(unittest.TestCase):
    def test_read_csv(self):
        csv_ret = FL96.process_csv_into_objects(fname='test_csv.csv', object_class=FL96.Target)
        assert csv_ret

class AssayTests(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()