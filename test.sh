#!/bin/bash

solver="z3" # cvc5 or z3

compare_with_solver() {
    eval $solver $1
    eval "python3" "py.py" $1
    echo "-----------------------------------------------"
}

problems=(
    "QF_LRA/check/bignum_lra1.smt2"
    "QF_LRA/check/bignum_lra2.smt2"
    "QF_LRA/clock_synchro/clocksynchro_2clocks.main_invar.base.smt2"
    "QF_LRA/sal/gasburner/gasburner-prop3-12.smt2"
    "QF_LRA/sal/gasburner/gasburner-prop3-5.smt2"
    "QF_LRA/DTP-Scheduling/constraints-cooking01.smt2"
    "QF_LRA/DTP-Scheduling/constraints-tms-2-3-light-10.smt2"
    "QF_LRA/sc/sc-5.induction.cvc.smt2"
    "QF_LRA/sal/windowreal/windowreal-no_t_deadlock-1.smt2"
    "QF_LRA/sal/windowreal/windowreal-safe-3.smt2"
    "QF_LRA/uart/uart-6.induction.cvc.smt2"
)

for p in "${problems[@]}"; do
    echo "$p";
    compare_with_solver "$p";
done
