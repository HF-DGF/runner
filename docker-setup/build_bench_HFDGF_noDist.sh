#!/bin/bash

. $(dirname $0)/build_bench_common.sh
set -x
# arg1 : Target project
# arg2~: Fuzzing targets
function build_with_HFDGF() {

    for TARG in "${@:2}"; do
        cd /benchmark

        str_array=($TARG)
        BIN_NAME=${str_array[0]}
        if  [[ $BIN_NAME == "readelf" || $BIN_NAME == "binutils-2.31.1" ]]; then
            BIT_OPT="-m32"
        else
            BIT_OPT=""
        fi

        arr=(${BIN_NAME//-/ })
        SIMPLE_BIN_NAME=${arr[0]}

        cd /benchmark
        CC="gclang"
        CXX="gclang++"
        build_target $1 $CC $CXX $BIT_OPT

        if  [[ "$BIN_NAME" == *"cjpeg"* || $BIN_NAME == "avconv" ]]; then
            build_target $1 $CC $CXX $BIT_OPT
        fi


        cd RUNDIR-$1
        get-bc $BIN_NAME || exit 1
        cd ..

        ### save prebuild to -pre
        # /benchmark/RUNDIR-$1 is used by build_common for real target so we use another
        rm -rf RUNDIR-$1-pre
        mv RUNDIR-$1 RUNDIR-$1-pre

        for BUG_NAME in "${str_array[@]:1}"; do
            # for every bug
            HFDGF_WORKDIR=/benchmark/RUNDIR-$1
            mkdir -p $HFDGF_WORKDIR
            cd $HFDGF_WORKDIR

            # copy the bc
            cp /benchmark/RUNDIR-$1-pre/$BIN_NAME.bc ./

            ### HFDGF-slicer
            # aflgo use stack-trace, windranger use line
            # cp /benchmark/target/stack-trace/$BIN_NAME/$BUG_NAME ./targets.txt
            cp /benchmark/target/HFDGF/$BIN_NAME/$BUG_NAME ./targets.txt
            time /HFDGF-slicer/build/bin/slicer --targets=./targets.txt ./$BIN_NAME.bc > slicer_log.txt
            cd ..

            # rebuild using HFDGF-clang-fast
            CC="/HFDGF-fuzzer/afl-clang-fast"
            CXX="/HFDGF-fuzzer/afl-clang-fast++"
            build_target $1 $CC $CXX "-fsanitize=address $BIT_OPT --HFDGFdir=$HFDGF_WORKDIR"

            ### copy results
            copy_build_result $1 $BIN_NAME $BUG_NAME "HFDGF-noDist"

            rm -rf $HFDGF_WORKDIR
            # mv $HFDGF_WORKDIR /benchmark/RUNDIR-$1-$BIN_NAME-$BUG_NAME
        done
    done

    rm -rf RUNDIR-$1-pre || exit 1

}

export SVF_DIR=/SVF
export LLVM_DIR=$SVF_DIR/llvm-13.0.1.obj
export Z3_DIR=$SVF_DIR/z3.obj
export PATH=/root/go/bin:$PATH
export LLVM_COMPILER_PATH=$LLVM_DIR/bin
export PATH=$LLVM_DIR/bin:$LLVM_DIR/lib:$PATH

# export HFDGF_EARLY_EXIT=true
# export DISABLE_DIST_CF=true
# export DISABLE_DIST_DF=true

# slicer 使用 AFLGo 的方法计算距离
export AFLGOCG=1
# 重新编译 slicer
bash /setup_HFDGF_slicer.sh


# Build with HFDGF
mkdir -p /benchmark/bin/HFDGF-noDist

build_with_HFDGF "libming-4.7" \
    "swftophp-4.7 2016-9827 2016-9829 2016-9831 2017-9988 2017-11728 2017-11729" &
build_with_HFDGF "libming-4.7.1" \
    "swftophp-4.7.1 2017-7578" &
build_with_HFDGF "libming-4.8" \
    "swftophp-4.8 2018-7868 2018-8807 2018-8962 2018-11095 2018-11225 2018-11226 2020-6628 2018-20427 2019-12982" &
build_with_HFDGF "libming-4.8.1" \
    "swftophp-4.8.1 2019-9114" &
build_with_HFDGF "lrzip-ed51e14" "lrzip-ed51e14 2018-11496" &
build_with_HFDGF "lrzip-9de7ccb" "lrzip-9de7ccb 2017-8846" &
build_with_HFDGF "binutils-2.26" \
    "cxxfilt 2016-4487 2016-4489 2016-4490 2016-4491 2016-4492 2016-6131" &
build_with_HFDGF "binutils-2.28" \
    "objdump 2017-8392 2017-8396 2017-8397 2017-8398" \
    "objcopy 2017-8393 2017-8394 2017-8395" &
build_with_HFDGF "binutils-2.31.1" "objdump-2.31.1 2018-17360" &
build_with_HFDGF "binutils-2.27" "strip 2017-7303" &
build_with_HFDGF "binutils-2.29" "nm 2017-14940" &
build_with_HFDGF "libxml2-2.9.4" \
  "xmllint 2017-5969 2017-9047 2017-9048" &
build_with_HFDGF "libjpeg-1.5.90" "cjpeg-1.5.90 2018-14498" &
build_with_HFDGF "libjpeg-2.0.4" "cjpeg-2.0.4 2020-13790" &

wait

build_with_HFDGF "binutils-2.29" "readelf 2017-16828"


# 恢复 slicer
export -n AFLGOCG
bash setup_HFDGF_slicer.sh
