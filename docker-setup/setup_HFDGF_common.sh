#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

dpkg --add-architecture i386
apt update -y
apt-get dist-upgrade -y
apt install -y nano wget curl build-essential git python3-dev python3-pip tmux sudo cmake libncurses5 zlib1g-dev unzip libtinfo5 libncurses5-dev libncursesw5-dev


# LLVM 13


# SVF
cd /
rm -rf SVF
git clone https://github.com/HF-DGF/SVF.git SVF
cd /SVF
git checkout 46018ceb5e09bda75c1c1fef163f40729769d1e5
bash ./build.sh
export PATH=/SVF/llvm-13.0.1.obj/bin:$PATH

cd /