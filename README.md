<!-- 
    README.md
    Written by @geveke.tom
    Febuary 2024
-->

## FL96 Script 

### Theory
$$ 
    a = 1 + 1 
$$

### Flowchart
![Flowchart](imgs/flowChart.png)

### Class Diagram
![Flowchart](imgs/classDiagram.png)

### Installation
Note: No additional dependencies are required, other than Python 3, which can be installed at [python.org](https://www.python.org/downloads/).
1. Clone git repository: 
    ```
    git clone https://github.com/tgeveke/FL96-Interview
    ```
2. Change into code directory
    ```
    cd FL96-Interview
    ```

### Usage
1. Run code using:
    ```
    python3 FL96.py
    ```
    or to execute unit tests in tests/tests.py:
    ```
    python3 FL96.py --run_tests
    ```
    or to specify specific paths to other precursor and/or target CSVs:
    ```
    python3 FL96.py --precursors_path "path/to/csv.csv" --targets_path "path/to/csv.csv"
    ```
