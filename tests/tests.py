import unittest
import os
import platform
import FL96

def windows_remove(path: str):
    os.system(f'del {path}')

def unix_remove(path: str):
    os.system(f'rm {path}')

os_name = platform.system()
if os_name == "Windows":
    rm = windows_remove
else:
    rm = unix_remove

class CSVTests(unittest.TestCase):    
    @staticmethod
    def generate_test_csv():
        pass

    def test_read_csv(self):
        csv_ret = FL96.AssayGenerator.process_csv_into_objects(fname='targets.csv', object_class=FL96.Target)
        assert isinstance(csv_ret[0], FL96.Target)

        csv_ret = FL96.AssayGenerator.process_csv_into_objects(fname='precursors.csv', object_class=FL96.Precursor)
        assert isinstance(csv_ret[0], FL96.Precursor)

class AssayGeneratorTests(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.assay_generator = FL96.AssayGenerator()
    
    def test_full(self):
        with open('test_precursors.csv', 'w') as file:
            file.write('Location,Precursor,Concentration (mol/L)\n')
            file.write('A1,Fe,1\n')
            file.write('A2,Zn,2\n')
            
        with open('test_targets.csv', 'w') as file:
            file.write('Location,Target ratio,Target volume (mL)\n')
            file.write('B1,Fe0.5Zn0.5,3.0\n')

        assay_generator = FL96.AssayGenerator(
            precursors_fname='test_precursors.csv',
            targets_fname='test_targets.csv',
            output_fname='test_assay.txt',
        )
        with open('test_assay.txt', 'r') as file:
            lines = file.readlines()
            assert lines[0] == 'transfer("A1", "B1", 2.0)\n'
            assert lines[1] == 'transfer("A2", "B1", 1.0)\n'
        
        rm('test_precursors.csv')
        rm('test_targets.csv')
        rm('test_assay.txt')

    def test_calculate_workflow_steps(self):
        self.assay_generator.calculate_workflow_steps()
        assert self.assay_generator.steps != []

    def test_find_element(self):
        precursor = self.assay_generator.find_element(element=self.assay_generator.precursors[0].precursor)
        assert precursor == self.assay_generator.precursors[0]

    def test_get_precursor_at(self):
        precursor = self.assay_generator.get_precursor_at(location=self.assay_generator.precursors[0].location)
        assert precursor == self.assay_generator.precursors[0]

    def test_get_target_at(self):
        target = self.assay_generator.get_target_at(location=self.assay_generator.targets[0].location)
        assert target == self.assay_generator.targets[0]

    def test_missing_precursor(self):
        prev_precursors = self.assay_generator.precursors
        self.assay_generator.precursors = prev_precursors.copy()
        self.assay_generator.precursors.pop(0)

        self.assertRaises(FL96.PrecursorMissingException, self.assay_generator.calculate_workflow_steps)

        self.assay_generator.precursors = prev_precursors

    def test_script_generation(self):
        prev_steps = self.assay_generator.steps
        prev_output_fname = self.assay_generator.output_fname
        self.assay_generator.output_fname = 'testing_assay.txt'
        self.assay_generator.steps = [
            ['A1', 'B1', 1.0],
            ['A1', 'B2', 2.0]
        ]
        self.assay_generator.generate_workflow_script()

        with open('testing_assay.txt', 'r') as file:
            lines = file.readlines()
            assert lines[0] == 'transfer("A1", "B1", 1.0)\n'
            assert lines[1] == 'transfer("A1", "B2", 2.0)\n'

        rm('testing_assay.txt')
        self.assay_generator.steps = prev_steps
        self.assay_generator.output_fname = prev_output_fname

class TargetTests(unittest.TestCase):
    def test_parse_target_ratio(self):
        target = FL96.Target()
        target.target_ratio = 'Fe0.5Zn0.5'
        target.parse_target_ratio()
        assert target.target_ratios == {'Fe': 0.5, 'Zn': 0.5}
    
    def test_add(self):
        target = FL96.Target()
        target.add(element='Zn', moles=1, volume=1.5)
        assert target.current_volume == 1.5
        assert target.current_makeup == {'Zn': 1.0}

if __name__ == '__main__':
    unittest.main()