#!/bin/bash

solver="z3" # cvc5 or z3

problem="QF_LRA/check/bignum_lra1.smt2"
eval $solver $problem
eval "python3" "py.py" $problem
echo "-----------------------------------------------"

problem="QF_LRA/check/bignum_lra2.smt2"
eval $solver $problem
eval "python3" "py.py" $problem
echo "-----------------------------------------------"

problem="QF_LRA/clock_synchro/clocksynchro_2clocks.main_invar.base.smt2"
eval $solver $problem
eval "python3" "py.py" $problem
echo "-----------------------------------------------"

problem="QF_LRA/sal/gasburner/gasburner-prop3-12.smt2"
eval $solver $problem
eval "python3" "py.py" $problem
echo "-----------------------------------------------"
