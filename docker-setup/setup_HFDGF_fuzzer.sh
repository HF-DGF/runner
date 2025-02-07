#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

# setup env
export SVF_DIR=/SVF
export LLVM_DIR=$SVF_DIR/llvm-13.0.1.obj
export Z3_DIR=$SVF_DIR/z3.obj
export PATH=/SVF/llvm-13.0.1.obj/bin:$PATH


# HFDGF fuzzer
cd /
rm -rf HFDGF-fuzzer
git clone https://github.com/HF-DGF/fuzzer.git HFDGF-fuzzer
cd HFDGF-fuzzer
make clean all && cd llvm_mode && make clean all

cd /
