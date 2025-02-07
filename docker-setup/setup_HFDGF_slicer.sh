#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

# setup env
export SVF_DIR=/SVF
export LLVM_DIR=$SVF_DIR/llvm-13.0.1.obj
export Z3_DIR=$SVF_DIR/z3.obj
export PATH=/SVF/llvm-13.0.1.obj/bin:$PATH

# HFDGF slicer
cd /
rm -rf HFDGF-slicer
git clone https://github.com/HF-DGF/slicer.git HFDGF-slicer
cd /HFDGF-slicer
# build
mkdir build; cd build
cmake .. && make
