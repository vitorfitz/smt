#!/bin/bash

solver="z3" # cvc5 or z3

problem="QF_LRA/check/bignum_lra1.smt2"
eval "python3" "py.py" $problem
eval $solver $problem
echo "-----------------------------------------------"

problem="QF_LRA/check/bignum_lra2.smt2"
eval "python3" "py.py" $problem
eval $solver $problem
echo "-----------------------------------------------"

problem="QF_LRA/spider_benchmarks/bad_echos_ascend.base.smt2"
eval "python3" "py.py" $problem
eval $solver $problem
echo "-----------------------------------------------"
