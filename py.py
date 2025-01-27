from pysmt.smtlib.parser import SmtLibParser
import sys
from pysmt.shortcuts import Not, And, Or, TRUE, FALSE, UnsatCoreSolver, Symbol
from pysmt.environment import get_env
from pysmt.typing import BOOL
from pysat.solvers import Glucose3
import time

aux_prefix="."  # Prefix for auxiliary variables
# Invalid variable name to avoid conflict with input variables

def boolean_abstraction(formula):
    """Abstracts the QF_LRA formula by replacing numerical comparison operations (>, >=, <, <=, =) with Boolean variables."""
    abstractions = []
    abst_indexes = {}
    boolean_vars = set()
    next_index = 1

    # Recursively traverse the formula
    def rec(formula):
        nonlocal next_index

        # Convert the Boolean operations to SymPy
        if formula.is_bool_constant():
            return formula
        if formula.is_bool_op() or formula.is_ite():
            return get_env().formula_manager.create_node(
                formula.node_type(),
                tuple(rec(arg) for arg in formula.args())
            )

        # Abstract the comparison operations between reals
        if (
            formula.is_equals() or
            formula.is_lt() or
            formula.is_le()
        ):
            # Handle formulas with real operators nested inside ITEs, like:
            # a > (b? 1: 2)
            # Rewritten to: (b and a>1) or (not b and a>2)
            def ite_substitution(pos, replacement):
                return get_env().formula_manager.create_node(
                    formula.node_type(),
                    tuple(replacement if i == pos else arg for i,
                          arg in enumerate(formula.args())),
                )

            for i, ite in enumerate(formula.args()):
                if ite.is_ite():
                    return Or(
                        rec(And(ite.arg(0), ite_substitution(i, ite.arg(1)))),
                        rec(And(Not(ite.arg(0)), ite_substitution(i, ite.arg(2)))),
                    )

            if formula not in abst_indexes:
                abst_indexes[formula] = next_index
                next_index += 1
                abstractions.append(formula)
            return Symbol(aux_prefix+str(abst_indexes[formula]), BOOL)

        if formula.is_literal():
            boolean_vars.add(formula)
            return formula

        raise ValueError(
            "Unexpected literal or operator in formula \""+str(formula)+"\"")

    return rec(formula), abstractions, abst_indexes, boolean_vars

def to_cnf(formula, num_aux_vars=0):
    """
    Convert a Boolean formula to CNF using Tseitin transformation.
    """
    def get_aux_var():
        nonlocal num_aux_vars
        num_aux_vars+=1
        s=Symbol(aux_prefix+str(num_aux_vars))
        return s
    
    clauses=[]
    def rec(formula):
        if formula.is_bool_constant() or formula.is_literal():
            return formula
        
        not_flag=False
        if formula.is_not():
            not_flag=True
            formula=formula.arg(0)
            if formula.is_true():
                return FALSE()
            elif formula.is_false():
                return TRUE()

        # Convert everything to "and", "or" and "not"
        if formula.is_implies():
            formula=Or(Not(formula.arg(0)), formula.arg(1))

        elif formula.is_iff():
            formula=And(
                Or(Not(formula.arg(0)), formula.arg(1)),
                Or(formula.arg(0), Not(formula.arg(1))),
            )

        elif formula.is_ite():
            formula=Or(
                And(formula.arg(0), formula.arg(1)),
                And(Not(formula.arg(0)), formula.arg(2)),
            )
        
        # Apply Tseitin transformations
        if formula.is_and() or formula.is_or():
            aux_var = get_aux_var()
            if not_flag:
                aux_var=Not(aux_var)
            sub_aux_vars = [rec(arg) for arg in formula.args()]

            if formula.is_and():
                filtered_aux=[]
                for sub_aux in sub_aux_vars:
                    if sub_aux.is_true():
                        continue
                    elif sub_aux.is_false():
                        return TRUE() if not_flag else FALSE()
                    filtered_aux.append(sub_aux)
                    clauses.append(Or(Not(aux_var), sub_aux))

                clauses.append(Or(aux_var, *[Not(sub) for sub in filtered_aux]))

            else: # formula.is_or():
                filtered_aux=[]
                for sub_aux in sub_aux_vars:
                    if sub_aux.is_false():
                        continue
                    elif sub_aux.is_true():
                        return FALSE() if not_flag else TRUE()
                    filtered_aux.append(sub_aux)
                    clauses.append(Or(aux_var, Not(sub_aux)))

                clauses.append(Or(Not(aux_var), *filtered_aux))
            return aux_var

        raise Exception(f"Unsupported formula type: {formula}")

    top_aux = rec(formula)
    clauses.append(top_aux)  # Ensure the top-level formula holds

    # Combine all clauses into a CNF
    return And(*clauses)

# Parse the SMT-LIB file
if len(sys.argv) < 2:
    print("Input file name required")
    sys.exit(1)
file_path = sys.argv[1]

parser = SmtLibParser()
script = parser.get_script_fname(file_path)
formula = script.get_last_formula()
start_time=time.perf_counter()

# Convert the formula to CNF
bool_formula, abstractions, abst_indexes, boolean_vars = boolean_abstraction(
    formula)

num_aux_vars = len(abstractions)
bool_vars_dict = {}
for var in boolean_vars:
    num_aux_vars += 1
    bool_vars_dict[var] = num_aux_vars

cnf_formula = to_cnf(bool_formula,num_aux_vars)
if cnf_formula.is_false():
    print("unsat")
    exit(0)

# Convert CNF formula into a list of clauses
clauses = []
if not formula.is_true():
    for clause in cnf_formula.args():
        if clause.is_literal():
            vars=[clause]
        else:
            vars=[lit for lit in clause.args()]
        
        nums=[]
        for var in vars:
            # Get variable name
            name = str(var).strip(" '!()")
            
            if name.startswith(aux_prefix):
                # Is an auxiliary variable
                nums.append(int(name[len(aux_prefix):])*(-1 if var.is_not() else 1))

            else: # Is a variable from the input
                lit2 = var
                if var.is_not():
                    lit2 = var.arg(0)
                nums.append(bool_vars_dict[lit2]*(-1 if var.is_not() else 1))

        if len(nums)>0:
            clauses.append(nums)

# Add dummy clauses for variables that were simplified out
unused_vars = set(i for i in range(1, len(abstractions)+1))
for c in clauses:
    for var in c:
        try:
            unused_vars.remove(abs(var))
        except:
            pass
for u in unused_vars:
    clauses.append([-u, u])

# Add clauses to SAT solver
sat_solver = Glucose3()
for c in clauses:
    sat_solver.add_clause(c)

lra_solver=UnsatCoreSolver(name="z3", logic="QF_LRA")
while True:
    # Get a solution of the abstracted SAT problem
    if sat_solver.solve():
        model = sat_solver.get_model()

        # Check if solution is valid for the full problem
        lra_solver.reset_assertions()
        for var in model:
            if abs(var)-1 < len(abstractions):
                if var > 0:
                    lra_solver.add_assertion(abstractions[var-1])
                else:
                    lra_solver.add_assertion(Not(abstractions[-var-1]))

        if lra_solver.solve():
            # Solution is valid and can be returned
            print("sat")
            # print(s.get_model())
            break
        else:
            # Solution is invalid. Negate the unsatisfiable core and add it as a clause to the SAT solver
            unsat_core = lra_solver.get_unsat_core()
            new_clause = []
            for expr in unsat_core:
                if expr in abst_indexes:
                    new_clause.append(-abst_indexes[expr])
                elif Not(expr) in abst_indexes:
                    new_clause.append(abst_indexes[Not(expr)])
                else:
                    raise ValueError(
                        "Unexpected clause \""+str(expr)+"\" in Unsat Core")
            sat_solver.add_clause(new_clause)
            pass
    else:
        # Ran out of solutions
        print("unsat")
        break

end_time=time.perf_counter()
total_seconds = end_time - start_time
print(str(round(total_seconds*1000))+" ms")