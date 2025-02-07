#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

dpkg --add-architecture i386
apt update -y
apt-get dist-upgrade -y
apt install -y nano wget curl build-essential git python3 python3-dev python3-pip tmux sudo cmake libncurses5 zlib1g-dev unzip libtinfo5 libncurses5-dev libncursesw5-dev


# SVF
cd /
git clone https://github.com/HF-DGF/SVF.git SVF
cd /SVF
git checkout 46018ceb5e09bda75c1c1fef163f40729769d1e5
bash ./build.sh
export PATH=/SVF/llvm-13.0.1.obj/bin:$PATH


# HFDGF slicer
cd /
git clone https://github.com/HF-DGF/slicer.git HFDGF-slicer
cd /HFDGF-slicer
# setup env
export SVF_DIR=/SVF
export LLVM_DIR=$SVF_DIR/llvm-13.0.1.obj
export Z3_DIR=$SVF_DIR/z3.obj
# build
mkdir build; cd build
cmake .. && make


# HFDGF fuzzer
cd /
git clone https://github.com/HF-DGF/fuzzer.git HFDGF-fuzzer
cd HFDGF-fuzzer
make clean all && cd llvm_mode && make clean all

cd /
