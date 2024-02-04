
'''
    FL96.py
    Written by @geveke.tom
    Febuary 2024
'''

# ---------- Imports ---------- #
import csv

# ---------- Classes ---------- #
class Material:
    def __init__(self) -> None:
        self.location: str
    
class Precursor(Material):
    def __init__(self) -> None:
        super().__init__()
        self.concentration: int or float


class Target(Material):
    def __init__(self) -> None:
        super().__init__()
        self.target_ratio: str
        self.target_ratios: dict
        self.target_volume: int or float

        self.current_volume = 0
        self.current_makeup = {}

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


# ---------- Methods ---------- #
def find_element(element, precursors) -> Precursor:
    for precursor in precursors:
        if precursor.precursor == element:
            return precursor
    return None

def calculate_workflow_steps(precursors: list[Precursor], targets: list[Target]) -> list:
    steps = []
    
    for target in targets:
        target.parse_target_ratio()

        target.target_volume = float(target.target_volume)
        target_volume_ml = target.target_volume

        for element, ratio in target.target_ratios.items():
            precursor = find_element(element, precursors)
            if precursor is None:
                raise RuntimeError(f'No precusor for {element} found')
            
            concentration_mol_per_l = float(precursor.concentration)

            # Calculate volumes and ratios based on the modified algorithm
            target_moles = ratio * (target_volume_ml / 1000)  # Convert target volume to liters
            volume_l = target_moles / concentration_mol_per_l
            volume_ml = round(volume_l * 1000, 3)

            steps.append([precursor.location, target.location, volume_ml])

    if not check_workflow(steps, precursors, targets):
        raise RuntimeError('Workflow check returned False')
    
    return steps

def check_workflow(steps, precursors, targets) -> bool:
    def get_precursor_at(location) -> Precursor:
        for precursor in precursors:
            if precursor.location == location:
                print(f'precursor at location: {location} = {precursor.precursor}')
                return precursor
        return None
            
    def get_target_at(location) -> Target:
        for target in targets:
            if target.location == location:
                print(f'target at location: {location} = {target.target_ratios}')
                return target
        return None

    for step in steps:
        start_location, end_location, volume = step
        precursor = get_precursor_at(start_location)
        target = get_target_at(end_location)

        element = precursor.precursor
        moles = float(precursor.concentration) * volume

        target.add(element, moles, volume)

        # input('next step?')

    for target in targets:
        print(target.target_ratios)
        print(target.current_makeup)
        if target.current_volume != target.target_volume:
            print(f'current volume {target.current_volume} != target volume {target.target_volume}')
        for element, target_ratio in target.target_ratios.items():
            print(f'Checking {element} with ratio: {target_ratio}')
            if element not in target.current_makeup.keys():
                print(f'{element} not in {target.current_makeup.keys()}')
                return False
            if abs(target_ratio - target.current_makeup[element] / target.target_volume) > 1e-5:
                print(f'{element} target {target_ratio} != current {target.current_makeup[element] / target.current_volume}')
                return False
        break
    
    return True

def generate_workflow_script(steps, output_fname: str) -> None:
    def generate_step_string(start_location: str, end_location: str, quantity: float or int):
        return f'transfer("{start_location}", "{end_location}", {quantity})\n'
    
    steps_strings = [
        generate_step_string(*step) for step in steps
    ]
    
    with open(output_fname, 'w') as output_file:
        output_file.writelines(steps_strings)

    print(f'Successfully saved robot script at: {output_fname}')
    with open(output_fname, 'r') as output_file:
        [print(f'\t{line}') for line in output_file.readlines()]
    

def process_csv_into_objects(fname: str, object_class) -> list:
    objects = []
    with open(fname, 'r', encoding='utf-8-sig') as csv_file:
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

def main():
    # precursors_fname = 'precursors.csv'
    precursors_fname = r'/Users/tom/Downloads/FL96/precursors.csv'
    targets_fname = r'/Users/tom/Downloads/FL96/targets.csv'
    output_fname = 'assay.txt'

    precursors = process_csv_into_objects(precursors_fname, Precursor)
    targets = process_csv_into_objects(targets_fname, Target)

    steps = calculate_workflow_steps(
        precursors=precursors,
        targets=targets,
    )
    generate_workflow_script(
        steps=steps,
        output_fname=output_fname
    )

if __name__ == '__main__':
    import os
    os.system('clear')
    main()
