from pysmt.smtlib.parser import SmtLibParser
from sympy.logic.boolalg import to_cnf
import sys
from pysmt.shortcuts import Not, UnsatCoreSolver
import sympy
from pysat.solvers import Glucose3

def boolean_abstraction(pysmt_formula):
    """Abstracts the QF_LRA formula by replacing numerical comparison operations (>, >=, <, <=, =) with Boolean variables."""
    abstractions=[]
    abst_indexes={}
    next_index=1

    # Recursively traverse the formula
    def rec(pysmt_formula):
        nonlocal next_index

        # Convert the Boolean operations to SymPy
        if pysmt_formula.is_true():
            return True
        if pysmt_formula.is_false():
            return False
        if pysmt_formula.is_not():
            return sympy.Not(rec(pysmt_formula.arg(0)))
        if pysmt_formula.is_and():
            return sympy.And(*[rec(arg) for arg in pysmt_formula.args()])
        if pysmt_formula.is_or():
            return sympy.Or(*[rec(arg) for arg in pysmt_formula.args()])
        if pysmt_formula.is_ite():
            return sympy.ITE(*[rec(arg) for arg in pysmt_formula.args()])
        if pysmt_formula.is_implies():
            return sympy.Implies(*[rec(arg) for arg in pysmt_formula.args()])
        
        # Abstract the comparison operations between reals
        if not(
            pysmt_formula.is_equals() or
            pysmt_formula.is_lt() or
            pysmt_formula.is_le()
        ):
            raise ValueError(f"Unsupported PySMT formula: {pysmt_formula}")

        formula_str=str(pysmt_formula)
        if formula_str not in abst_indexes:
            abst_indexes[formula_str]=next_index
            next_index+=1
            abstractions.append(pysmt_formula)
        return sympy.symbols(str(abst_indexes[formula_str]))
    
    return rec(pysmt_formula),abstractions,abst_indexes

# Parse the SMT-LIB file
if len(sys.argv)<2:
    print("Input file name required")
    sys.exit(1)
file_path=sys.argv[1]

parser = SmtLibParser()
script = parser.get_script_fname(file_path)
formula = script.get_last_formula()

# Convert the formula to CNF
bool_formula,abstractions,abst_indexes=boolean_abstraction(formula)
cnf_formula = to_cnf(bool_formula)

# Convert CNF formula into a list of clauses
clauses = []
for clause in cnf_formula.args:
    if clause.is_Atom:
        clauses.append([int(str(clause))])
    else:
        clauses.append([int(str(lit)) for lit in clause.args])

# Add clauses to SAT solver
sat_solver = Glucose3()
for c in clauses:
    sat_solver.add_clause(c)

while True:
    # Get a solution of the abstracted SAT problem
    if sat_solver.solve():
        model=sat_solver.get_model()

        with UnsatCoreSolver(name="z3", logic="QF_LRA") as s:
            # Check if solution is valid for the full problem
            for var in model:
                if var>0:
                    s.add_assertion(abstractions[var-1])
                else:
                    s.add_assertion(Not(abstractions[-var-1]))
            
            if s.solve():
                # Solution is valid and can be returned
                print("sat")
                print(s.get_model())
                break
            else:
                # Solution is invalid. Negate the unsatisfiable core and add it as a clause to the SAT solver
                unsat_core = s.get_unsat_core()
                new_clause=[]
                for expr in unsat_core:
                    new_clause.append(-abst_indexes[str(expr)])
                sat_solver.add_clause(new_clause)
                pass
    else:
        # Ran out of solutions
        print("unsat")
        break