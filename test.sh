#!/bin/bash

solver="z3" # cvc5 or z3

compare_with_solver() {
    eval $solver $1
    eval "python3" "py.py" $1
    echo "-----------------------------------------------"
}

problems=(
    "inputs/easy_sat.smt2"
    "inputs/easy_unsat.smt2"
    "inputs/hard_sat.smt2"
    "inputs/hard_unsat.smt2"
    "inputs/bignum_lra1.smt2"
    "inputs/bignum_lra2.smt2"
    "inputs/clocksynchro_2clocks.main_invar.base.smt2"
    "inputs/gasburner-prop3-12.smt2"
    "inputs/gasburner-prop3-5.smt2"
    "inputs/constraints-cooking01.smt2"
    "inputs/constraints-tms-2-3-light-10.smt2"
    "inputs/sc-5.induction.cvc.smt2"
    "inputs/windowreal-no_t_deadlock-1.smt2"
    "inputs/windowreal-safe-3.smt2"
)

for p in "${problems[@]}"; do
    echo "$p";
    compare_with_solver "$p";
done
