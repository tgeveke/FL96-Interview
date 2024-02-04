
'''
    FL96.py
    Written by @geveke.tom
    Febuary 2024
'''

# ---------- Imports ---------- #
import csv
import math

# ---------- Custom Exceptions ---------- #
class InvalidWorkflowException(RuntimeError):
    pass

class PrecursorMissingException(RuntimeError):
    pass

# ---------- Classes ---------- #
class Material:
    def __init__(self) -> None:
        self.location: str
    
class Precursor(Material):
    def __init__(self) -> None:
        super().__init__()
        self.concentration: int or float
    
    def __str__(self) -> str:
        return f'Precursor of element {self.precursor} at location: {self.location} with concentration {self.concentration} M/L'

class Target(Material):
    def __init__(self) -> None:
        super().__init__()
        self.target_ratio: str
        self.target_ratios: dict
        self.target_volume: int or float

        self.current_volume = 0
        self.current_makeup = {}

    def __str__(self) -> str:
        return f'Target with makeup {self.target_ratio} at location: {self.location} with target volume {self.target_volume} mL'


    def add(self, element, moles, volume):
        if element in self.current_makeup:
            print(f'element {element} already in target')
            self.current_makeup[element] += moles
        else:
            self.current_makeup[element] = moles

        self.current_volume += volume

    def parse_target_ratio(self):
        quantities = {}
        was_last_numeric: bool = False
        current_element = ''
        current_quantity_str = ''
        for char_id, char in enumerate(self.target_ratio):
            if char.isalpha() and was_last_numeric:
                quantities[current_element] = float(current_quantity_str)
                current_element = ''
                current_quantity_str = ''
            if char.isnumeric() or char == '.':
                current_quantity_str += char
            else:
                current_element += char
            was_last_numeric = char.isnumeric()

            if char_id + 1 == len(self.target_ratio):
                quantities[current_element] = float(current_quantity_str)

        self.target_ratios = quantities
        return self.target_ratios
    
class AssayGenerator:
    def __init__(self, 
                 precursors_fname: str = 'precursors.csv',
                 targets_fname: str = 'targets.csv',
                 output_fname: str = 'assays/assay.txt') -> None:
        self.output_fname = output_fname

        self.precursors = self.process_csv_into_objects(precursors_fname, Precursor)
        self.targets = self.process_csv_into_objects(targets_fname, Target)
        self.steps = []
        self.calculate_workflow_steps()
        self.generate_workflow_script()

    def find_element(self, element) -> Precursor:
        for precursor in self.precursors:
            if precursor.precursor == element:
                return precursor
        return None
    
    def get_precursor_at(self, location) -> Precursor:
            for precursor in self.precursors:
                if precursor.location == location:
                    return precursor
            return None
                
    def get_target_at(self, location) -> Target:
        for target in self.targets:
            if target.location == location:
                return target
        return None

    def calculate_workflow_steps(self) -> list:
        steps = []
        for target in self.targets:
            target.parse_target_ratio() # Step which converts string makeup eg "Fe0.5Zn0.5" to dictionary {"Fe": 0.5, "Zn": 0.5}
            target.target_volume = float(target.target_volume)
            target_volume_ml = target.target_volume

            target_sum_volume = 0
            precursor_volumes = {}
            precursor_ratios = {}
            for element, target_ratio in target.target_ratios.items():
                precursor = self.find_element(element)
                if precursor is None:
                    raise PrecursorMissingException(f'Precursor {element} is missing, which is needed in {target}')
                concentration_mol_per_l = float(precursor.concentration)  # Concentration in mol/L
                volume_l = target_ratio / concentration_mol_per_l  # Convert moles to volume in liters
                volume_ml = volume_l * 1000  # Convert volume to mL
                precursor_volumes[element] = volume_ml
                precursor_ratios[element] = target_ratio

                target_sum_volume += volume_ml

            # Scale volumes and ratios to meet the desired total volume
            scale_factor = target_volume_ml / target_sum_volume
            scaled_sum_volumes = 0
            scaled_ratios = {}
            for element in precursor_volumes:
                precursor = self.find_element(element)
                precursor_volumes[element] *= scale_factor
                scaled_sum_volumes += precursor_volumes[element]
                scaled_ratios[element] = precursor_ratios[element] * scale_factor

                steps.append([precursor.location, target.location, round(precursor_volumes[element], 4)])
            
            # Sanity check for target volume
            if not math.isclose(scaled_sum_volumes, target.target_volume, rel_tol=0.01):
                print(f'{scaled_sum_volumes, target.target_volume}')

        self.steps = steps

        # Run check_workflow(), which validates that running all generated steps will produce the correct targets
        workflow_success, workflow_message = self.check_workflow()
        if not workflow_success:
            raise InvalidWorkflowException(workflow_message)
        
        return steps
        
    def check_workflow(self) -> (bool, str):
        ''''
        Validates
        '''

        for target in self.targets:
            target.current_makeup = {}
            target.current_volume = 0

        for step in self.steps:
            start_location, end_location, volume = step
            precursor = self.get_precursor_at(start_location)
            if precursor is None:
                return False, f'No precursor at {start_location}'
            target = self.get_target_at(end_location)
            if target is None:
                return False, f'No target at {end_location}'

            element = precursor.precursor
            moles = float(precursor.concentration) * volume

            target.add(element, moles, volume)

        for target in self.targets:
            ratios = {element: value / sum(target.current_makeup.values()) for element, value in target.current_makeup.items()}
            if not math.isclose(target.current_volume, target.target_volume, rel_tol=0.01):
                return False, f'current volume {target.current_volume} != target volume {target.target_volume} for {target}'
            for element, target_ratio in target.target_ratios.items():
                if element not in ratios.keys():
                    return False, f'{element} not in {ratios.keys()} for target {target}'
                if not math.isclose(target_ratio, ratios[element], rel_tol=0.01):
                    return False, f'{element} target {target_ratio} != current {ratios[element]} for {target}'
        
        return True, 'Workflow is valid'

    def generate_workflow_script(self) -> None:
        def generate_step_string(start_location: str, end_location: str, quantity: float or int):
            return f'transfer("{start_location}", "{end_location}", {quantity})\n'
        
        steps_strings = [
            generate_step_string(*step) for step in self.steps
        ]
        
        with open(self.output_fname, 'w') as output_file:
            output_file.writelines(steps_strings)

        print(f'Successfully saved robot script at: {self.output_fname}')
        with open(self.output_fname, 'r') as output_file:
            for line in output_file.readlines():
                print(f'\t {line}')
        
    @staticmethod
    def process_csv_into_objects(fname: str, object_class) -> list:
        objects = []
        with open(fname, 'r', encoding='utf-8-sig') as csv_file: # Encoding is required due to "ufeff" in input csv
            csv_reader = csv.reader(csv_file)

            for row_id, row in enumerate(csv_reader):
                if row_id == 0:
                    attributes = row
                else:
                    myobject = object_class()
                    for attribute_id, attribute_name in enumerate(attributes):
                        attribute_name = attribute_name.lower()
                        attribute_name = attribute_name.split(' (')[0]
                        attribute_name = attribute_name.replace(' ', '_')
                        attribute_value = row[attribute_id]
                        setattr(myobject, attribute_name, attribute_value)
                    objects.append(myobject)
            return objects

if __name__ == '__main__':
    import os
    import argparse
    os.system('clear')

    parser = argparse.ArgumentParser(description='Process precursors and targets for liquid handling automation')
    parser.add_argument('--precursors_path', help='Path to the precursor CSV file')
    parser.add_argument('--targets_path', help='Path to the target CSV file')
    parser.add_argument('--run_tests', action='store_true', help='Run all available test cases')

    args = parser.parse_args()

    if args.run_tests:
        os.system('python3 -m unittest tests.tests')
    else:
        if not args.precursors_path or not args.targets_path:
            precursors_fname = 'precursors.csv'
            targets_fname = 'targets.csv'
        else:
            precursors_fname = args.precursor_path
            targets_fname = args.target_path

        # Call main script
        AssayGenerator(
            precursors_fname=precursors_fname,
            targets_fname=targets_fname
        )
