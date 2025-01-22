from pysmt.smtlib.parser import SmtLibParser
import sys
from pysmt.shortcuts import Not, And, Or, Ite, Implies, Iff, TRUE, FALSE, UnsatCoreSolver, Symbol
from pysmt.environment import get_env
from pysmt.typing import BOOL
from pysmt.operators import AND
from pysat.solvers import Glucose3


def boolean_abstraction(formula):
    """Abstracts the QF_LRA formula by replacing numerical comparison operations (>, >=, <, <=, =) with Boolean variables."""
    abstractions = []
    abst_indexes = {}
    boolean_vars = []
    next_index = 1

    # Recursively traverse the formula
    def rec(formula):
        nonlocal next_index

        # Convert the Boolean operations to SymPy
        if formula.is_bool_constant():
            return formula
        if formula.is_bool_op():
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
            if formula not in abst_indexes:
                abst_indexes[formula] = next_index
                next_index += 1
                abstractions.append(formula)
            return Symbol(str(abst_indexes[formula]), BOOL)

        if formula.is_literal():
            boolean_vars.append(formula)
            return formula

        raise ValueError(
            "Unexpected literal or operator in subformula \""+str(formula)+"\"")

    return rec(formula), abstractions, abst_indexes, boolean_vars

# Function to simplify CNF formulas represented as an array of sets


def remove_supersets(sets):
    sets = sorted(sets, key=len)
    result = []

    for i, s in enumerate(sets):
        if not any(s >= other for other in result):
            result.append(s)

    return result


def to_cnf(formula):
    # Base case
    if formula.is_bool_constant() or formula.is_literal():
        return formula

    # Convert everything to "and", "or" and "not"
    if formula.is_implies():
        return to_cnf(Or(Not(formula.arg(0)), formula.arg(1)))

    if formula.is_iff():
        return to_cnf(And(
            Or(Not(formula.arg(0)), formula.arg(1)),
            Or(formula.arg(0), Not(formula.arg(1))),
        ))

    if formula.is_ite():
        return to_cnf(And(
            Or(formula.arg(0), formula.arg(2)),
            Or(Not(formula.arg(0)), formula.arg(1)),
            Or(Not(formula.arg(1)), formula.arg(2)),
        ))

    # Apply commutative and distributive properties on OR
    if formula.is_or():
        or_args = set()
        and_args = set()
        for i, arg in enumerate(formula.args()):
            arg = to_cnf(arg)
            if arg.is_and():
                and_args.add(arg)
            elif arg.is_true():
                return TRUE()
            elif arg.is_false():
                continue
            elif arg.is_or():
                or_args.update(arg.args())
            else:
                or_args.add(arg)

        # a | !a == true
        for el in or_args:
            if Not(el) in or_args:
                return TRUE()

        distributed = [or_args]
        for i, arg in enumerate(and_args):
            dist2 = []
            for d in distributed:
                for j, arg2 in enumerate(arg.args()):
                    args3 = set()
                    if arg2.is_literal():
                        if Not(arg2) in d:  # a & !a == false
                            continue
                        args3.add(arg2)
                    else:
                        for arg3 in arg2.args():
                            if Not(arg3) in d:  # a & !a == false
                                args3 = None
                                break
                            args3.add(arg3)
                    if args3 != None:
                        d2 = d.copy()
                        d2.update(args3)
                        dist2.append(d2)
            distributed = remove_supersets(dist2)

        return And(Or(*d) for d in distributed)

    # Apply commutative property on AND
    if formula.is_and():
        args = set()
        for i, arg in enumerate(formula.args()):
            arg = to_cnf(arg)
            if arg.is_and():
                args.update(arg.args())
            elif arg.is_true():
                continue
            elif arg.is_false():
                return FALSE()
            else:
                args.add(arg)

        # a & !a == false
        for el in args:
            if Not(el) in args:
                return FALSE()

        return And(a for a in args)

    # Apply DeMorgan on NOT
    if formula.is_not():
        arg = formula.arg(0)
        if arg.is_and():
            return Or(*[to_cnf(Not(arg)) for arg in arg.args()])
        elif arg.is_or():
            return And(*[to_cnf(Not(arg)) for arg in arg.args()])
        elif arg.is_true():
            return FALSE()
        elif arg.is_false():
            return TRUE()


# Parse the SMT-LIB file
if len(sys.argv) < 2:
    print("Input file name required")
    sys.exit(1)
file_path = sys.argv[1]

parser = SmtLibParser()
script = parser.get_script_fname(file_path)
formula = script.get_last_formula()

# Convert the formula to CNF
bool_formula, abstractions, abst_indexes, boolean_vars = boolean_abstraction(
    formula)
cnf_formula = to_cnf(bool_formula)

if cnf_formula.is_false():
    print("unsat")
    exit(0)

# Convert CNF formula into a list of clauses
def get_clause_number(lit):
    ret = str(lit).strip(" '!()")
    return int(ret)*(-1 if lit.is_not() else 1)

clauses = []
if not formula.is_true():
    for clause in cnf_formula.args():
        if clause.is_literal():
            clauses.append([get_clause_number(clause)])
        else:
            clauses.append([get_clause_number(lit) for lit in clause.args()])

    num_added_vars = len(abstractions)
    for var in boolean_vars:
        num_added_vars += 1
        if var.is_not():
            clauses.append(-num_added_vars)
        else:
            clauses.append(num_added_vars)

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

while True:
    # Get a solution of the abstracted SAT problem
    if sat_solver.solve():
        model = sat_solver.get_model()

        with UnsatCoreSolver(name="z3", logic="QF_LRA") as s:
            # Check if solution is valid for the full problem
            for var in model:
                if var > 0:
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
