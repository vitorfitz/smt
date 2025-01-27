from z3 import Solver, parse_smt2_file, sat, unsat, unknown
import sys
import time

def solve_smt_problem(file_path):
    """
    Solves an SMT problem presented in an SMT-LIB file using the Z3 solver.

    :param file_path: Path to the SMT-LIB file
    """
    try:
        # Parse the SMT-LIB file
        formula = parse_smt2_file(file_path)
        start_time=time.perf_counter()
        
        # Initialize the solver
        solver = Solver()
        
        # Add the parsed formula to the solver
        solver.add(formula)
        
        # Check satisfiability
        result = solver.check()
        
        if result == sat:
            print("sat")
            # print(solver.model())
        elif result == unsat:
            print("unsat")
        elif result == unknown:
            print("unknown")
        else:
            print(f"Unexpected result: {result}")

        end_time=time.perf_counter()
        total_seconds = end_time - start_time
        print(str(round(total_seconds*1000))+" ms")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Path to the SMT-LIB file (modify this to the correct file path)
    file_path = sys.argv[1]
    
    # Solve the SMT problem
    solve_smt_problem(file_path)