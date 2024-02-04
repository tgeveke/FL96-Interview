
'''
    FL96.py
    Written by @geveke.tom
    Febuary 2024
'''

# ---------- Imports ---------- #
import csv

# ---------- Classes ---------- #
class Material:
    name: str
    location: str
    contains: []
    
class Precursor(Material):
    concentration: int or float


class Target(Material):
    target_ratio: float
    target_ratios: dict
    target_volume: int or float
    target_ratio_str: int or float

    current_volume = 0
    current_makeup = {}

    def add(self, element, moles, volume):
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

def calculate_workflow_steps(precursors: list[Precursor], targets: list[Target]) -> list:
    steps = []
    for target in targets:
        print()
        target_volume = float(target.target_volume)

        target.parse_target_ratio()
        print(target.target_ratios)
        for element, ratio in target.target_ratios.items():
            precursor = find_element(element, precursors)
            concentration = float(precursor.concentration)

            pure_mL_needed = ratio * target_volume
            volume_needed = (pure_mL_needed * concentration)
            print(f'{element} (target {ratio}/{target_volume}) requires {pure_mL_needed} mL with concentration: {concentration} M/L, meaning {volume_needed} mL of precursor is required')

            steps.append([precursor.location, target.location, volume_needed])

    if not check_workflow(steps, precursors, targets):
        raise RuntimeError
    
    return steps

def check_workflow(steps, precursors, targets) -> bool:
    def get_precusor_at(location) -> Precursor:
        for precursor in precursors:
            if precursor.location == location:
                return precursor
            
    def get_target_at(location) -> Target:
        for target in targets:
            if target.location == location:
                return target

    for step in steps:
        start_location, end_location, volume = step
        precursor = get_precusor_at(start_location)
        target = get_target_at(end_location)

        element = precursor.precursor
        moles = float(precursor.concentration) * volume

        target.add(element, moles, volume)
    
    for target in targets:
        for element, quantity in target.target_ratios.items():
            if element not in target.current_makeup.keys():
                print(f'{element} not in {target.current_makeup.keys()}')
                return False
            if quantity != target.current_makeup[element]:
                print(f'{element} {quantity} != {target.current_makeup[element]}')
                return False


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
    precursors_fname = 'precursors.csv'
    targets_fname = 'targets.csv'
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
    # main()

    target = {'Fe': 0.5, 'Zn': 0.5} #, 'Mg': 0.2}
    target_volume = 3
    # liqs = {'Fe': 0.5, 'Zn': 1}
    liqs = {'Fe': 1, 'Zn': 2, 'Mg': 1.5}

    current = {}
    current_volume = 0
    for element, ratio in target.items():
        moles_required = ratio * target_volume
        print(moles_required)

        volume_required = moles_required * (liqs[element])# / 1000)
        print(volume_required)

        current[element] = moles_required
        current_volume += volume_required

    volume_ratio = target_volume / current_volume
    print(volume_ratio)
    for key, value in current.items():
        current[key] *= volume_ratio
    ratios = {key: value / sum(current.values()) for key, value in current.items()}
    print(current)
    print(ratios)
    print(current_volume)

