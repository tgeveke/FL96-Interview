
'''
    FL96.py
    Written by @geveke.tom
    Febuary 2024
'''

# ---------- Imports ---------- #
import csv
import math
import os

# ---------- Custom Exceptions ---------- #
class InvalidWorkflowException(RuntimeError):
    pass

class PrecursorMissingException(RuntimeError):
    pass

# ---------- Classes ---------- #
class Material:
    '''
    Base class shared by Precusor and Target, 
    containing location information
    '''
    def __init__(self) -> None:
        self.location: str
    
class Precursor(Material):
    '''
    Inherited Matieral class for storing a single precursor 
    '''
    def __init__(self) -> None:
        super().__init__()
        self.concentration: int or float
    
    def __str__(self) -> str:
        '''
        Returns a human-readable string representation of the precursor containing important information
        '''
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
        '''
        Returns a human-readable string representation of the target containing important information
        '''
        return f'Target with makeup {self.target_ratio} at location: {self.location} with target volume {self.target_volume} mL'


    def add(self, element: str, moles: int or float, volume: int or float):
        '''
        Method used in check_workflow() to verify that the generated steps produce the desired output
        '''
        if element in self.current_makeup:
            # Not necessary for given test cases, but helpful for debug
            print(f'element {element} already in target')
            self.current_makeup[element] += moles
        else:
            self.current_makeup[element] = moles

        self.current_volume += volume

    def parse_target_ratio(self):
        '''
        Method called in generate_workflow_script() for each target.
        
        Uses self.target_ratio (string read from csv) to generate self.target_ratios,
            a dictionary in the form {element: element_ratio, ...}
        '''
        quantities = {} # Main variable to track the elements and quantities in the target ratio
        was_last_numeric: bool = False
        current_element = ''
        current_quantity_str = ''
        for char_id, char in enumerate(self.target_ratio):
            # Iterate over each character
            if char.isalpha() and was_last_numeric:
                # If at a letter and was last at a number, we have reached a new element
                quantities[current_element] = float(current_quantity_str) # Convert string to float and add to dictionary
                current_element = '' # Reset variables
                current_quantity_str = ''
            if char.isnumeric() or char == '.':
                # Character is part of the ratio (eg. 0.1)
                current_quantity_str += char
            else:
                # Character is part of the element (eg. Fe)
                current_element += char

            was_last_numeric = char.isnumeric() # Track if this character was a number for next iteration

            if char_id + 1 == len(self.target_ratio):
                # If at the end of the string, add the current quanity to the dictionary
                quantities[current_element] = float(current_quantity_str)

        self.target_ratios = quantities # Set member variable
        return self.target_ratios
    
class AssayGenerator:
    '''
    Main class for generating the assay scripts.
    
    args:
        precursors_fname: str = 'precursors.csv',
        targets_fname: str = 'targets.csv',
        output_fname: str = 'assays/assay.txt'
    
    methods:
        calculate_workflow_steps()
        check_workflow()
        find_element()
        generate_workflow_script()
        get_precursor_at()
        get_target_at()
        process_csv_into_objects()
    
    attributes:
        output_fname: str
        precursors: list[Precursor]
        targets: list[Target]
        steps: list[list[str, str, int or float]]
    '''
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

    def find_element(self, element: str) -> Precursor or None:
        '''
        Returns precursor object of argument element: str,
            or None if no precursor is found for the given element
        '''
        for precursor in self.precursors:
            if precursor.precursor == element:
                return precursor
        return None
    
    def get_precursor_at(self, location: str) -> Precursor or None:
        '''
        Returns precursor object at argument location: str,
            or None if no precursor is found at the given location
        '''
        for precursor in self.precursors:
            if precursor.location == location:
                return precursor
        return None
                
    def get_target_at(self, location: str) -> Target or None:
        '''
        Returns target object at argument location: str,
            or None if no target is found at the given location
        '''
        for target in self.targets:
            if target.location == location:
                return target
        return None

    def calculate_workflow_steps(self) -> list:
        '''
        Main method for generating the workflow steps,
            given self.precursors and self.targets.
        Takes no arguments, returns a list of steps 
        Note: the method sets self.steps to generated steps before calling check_workflow()
        '''
        steps = []
        for target in self.targets:
            # Go through each target from the CSV
            target.parse_target_ratio() # Step which converts string makeup eg "Fe0.5Zn0.5" to dictionary {"Fe": 0.5, "Zn": 0.5}
            target.target_volume = float(target.target_volume)
            target_volume_ml = target.target_volume

            # Set some initial variables for each target
            target_sum_volume = 0
            precursor_volumes = {}
            precursor_ratios = {}
            for element, target_ratio in target.target_ratios.items():
                # Go through each element and it's ratio in the target
                precursor = self.find_element(element)
                if precursor is None:
                    # This is bad news, means that no precursor can be found to create the target's makeup
                    raise PrecursorMissingException(f'Precursor {element} is missing, which is needed in {target}')
                
                concentration_mol_per_l = float(precursor.concentration)  # Concentration in mol/L
                volume_l = target_ratio / concentration_mol_per_l  # Convert moles to volume in liters
                volume_ml = volume_l * 1000  # Convert volume to mL
                precursor_volumes[element] = volume_ml # Track changes in dictionaries
                precursor_ratios[element] = target_ratio

                # Track changes to the volume to achieve 1 Mole of the target's makeup
                target_sum_volume += volume_ml

            # Scale volumes and ratios to meet the desired total volume, based on the volume to create 1 Mole of target
            scale_factor = target_volume_ml / target_sum_volume # Calculate scale factor
            scaled_sum_volumes = 0 # Scaled volume variable for sanity checks
            for element in precursor_volumes:
                # Reiterate over the elements
                precursor = self.find_element(element)
                precursor_volumes[element] *= scale_factor # Scale by the above scale factor
                scaled_sum_volumes += precursor_volumes[element] # Keep track of new volume

                # Now we can add the step with the scaled volume (rounded to 4 digits)
                steps.append([precursor.location, target.location, round(precursor_volumes[element], 4)])
            
            # Sanity check for target volume
            if not math.isclose(scaled_sum_volumes, target.target_volume, rel_tol=0.01):
                # Something bad happened in the algorithm if this is called
                raise InvalidWorkflowException(f'{scaled_sum_volumes, target.target_volume}')

        # Set member variable self.steps before calling self.check_workflow()
        self.steps = steps

        # Run check_workflow(), which validates that running all generated steps will produce the correct targets
        workflow_success, workflow_message = self.check_workflow()
        if not workflow_success:
            raise InvalidWorkflowException(workflow_message)
        
        return steps
        
    def check_workflow(self) -> (bool, str):
        ''''
        Validates the generated steps in self.steps using target.add()
        
        Returns boolean workflow_success and string workflow_message
        '''

        for step in self.steps:
            # Run through each step in self.steps 
            start_location, end_location, volume = step

            precursor = self.get_precursor_at(start_location)
            if precursor is None:
                # If no precursor is found at the start location
                return False, f'No precursor at {start_location}'
            
            target = self.get_target_at(end_location)
            if target is None:
                # If no target is found at the end location
                return False, f'No target at {end_location}'

            element = precursor.precursor
            moles = float(precursor.concentration) * volume

            # Call target.add() to track each step's effect on the target
            target.add(element, moles, volume)

        for target in self.targets:
            # Now that all steps have been simulated, go through and check each target for correctness
            ratios = {element: value / sum(target.current_makeup.values()) for element, value in target.current_makeup.items()}
            if not math.isclose(target.current_volume, target.target_volume, rel_tol=0.01):
                # If the volume after all steps != the target volume
                return False, f'current volume {target.current_volume} != target volume {target.target_volume} for {target}'
            for element, target_ratio in target.target_ratios.items():
                if element not in ratios.keys():
                    # If element is completely missing after all steps
                    return False, f'{element} not in {ratios.keys()} for target {target}'
                if not math.isclose(target_ratio, ratios[element], rel_tol=0.01):
                    # If element ratio is incorrect in target after all steps
                    return False, f'{element} target {target_ratio} != current {ratios[element]} for {target}'
            
            # Reset changed variables for future calls to check_workflow()
            target.current_makeup = {}
            target.current_volume = 0

        # If nothing already triggered a return statement, the workflow is valid
        return True, 'Workflow is valid'

    def generate_workflow_script(self) -> None:
        '''
        Creates output assay script at self.output_fname,
            in the form transfer("{start_location}", "{end_location}", {quantity})\n
        '''
        def generate_step_string(start_location: str, end_location: str, quantity: float or int):
            return f'transfer("{start_location}", "{end_location}", {quantity})\n'

        # Call generate_step_string to format each line        
        steps_strings = [generate_step_string(*step) for step in self.steps]

        # Write the lines to self.output_fname
        with open(self.output_fname, 'w') as output_file:
            output_file.writelines(steps_strings)

        print(f'Successfully saved robot script at: {self.output_fname}')
        with open(self.output_fname, 'r') as output_file:
            # Print output steps for easy debug
            for line in output_file.readlines():
                print(f'\t {line}')
        
    @staticmethod
    def process_csv_into_objects(fname: str, object_class) -> list:
        '''
        Method to fill instantiated objects of type object class based on attributes
            supplied as column names from the csv (fname: str)

        Returns a list of the objects
        '''
        objects = []
        with open(fname, 'r', encoding='utf-8-sig') as csv_file: # Encoding is required due to "ufeff" in input csv
            csv_reader = csv.reader(csv_file)

            for row_id, row in enumerate(csv_reader):
                if row_id == 0:
                    # Get attributes to fill in objects based on first row (column headers)
                    attributes = row
                else:
                    myobject = object_class() # Instantiate object
                    for attribute_id, attribute_name in enumerate(attributes):
                        # For each attribute in each row, parse the columns and fill in the data
                        attribute_name = attribute_name.lower()
                        attribute_name = attribute_name.split(' (')[0]
                        attribute_name = attribute_name.replace(' ', '_')
                        attribute_value = row[attribute_id]
                        setattr(myobject, attribute_name, attribute_value) # Actual setting of member attribute
                    objects.append(myobject)
            return objects

if __name__ == '__main__':
    '''
    Main entry into script
    '''
    import argparse

    # Define arguments --precursors_path, --targets_path, and boolean --run_tests
    parser = argparse.ArgumentParser(description='Process precursors and targets for liquid handling automation')
    parser.add_argument('--precursors_path', help='Path to the precursor CSV file')
    parser.add_argument('--targets_path', help='Path to the target CSV file')
    parser.add_argument('--run_tests', action='store_true', help='Run all available test cases')

    args = parser.parse_args()
    if args.run_tests:
        # Just run unit tests
        os.system('python3 -m unittest tests.tests')
    else:
        # Run main script, first check if non-default CSV paths were supplied
        if not args.precursors_path:
            # Set to default file path
            precursors_fname = 'precursors.csv'
        else:
            # If user supplies a non-default path
            precursors_fname = args.precursor_path
        if not args.targets_path:
            targets_fname = 'targets.csv'
        else:
            targets_fname = args.target_path

        # Call AssayGenerator constructor, which will handle everything 
        assay_generator = AssayGenerator(
            precursors_fname=precursors_fname,
            targets_fname=targets_fname
        )
