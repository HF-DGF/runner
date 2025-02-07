#!/usr/bin/env python3

import os, shutil, subprocess, argparse, csv, sys, glob
from common import run_cmd, check_cpu_count, fetch_works
from benchmark import generate_slicing_worklist, SLICE_TARGETS

BASE_DIR = os.path.join("/benchmark")
SMAKE_OUT_DIR = os.path.join(BASE_DIR, "smake-out")
SPARROW_OUT_DIR = os.path.join(BASE_DIR, "tmp")
TARG_LOC_DIR = os.path.join(BASE_DIR, "target", "line")
DAFL_INPUT_DIR = os.path.join(BASE_DIR, "DAFL-input")
DAFL_NAIVE_INPUT_DIR = os.path.join(BASE_DIR, "DAFL-input-naive")
SPARROW_PATH = os.path.join('/sparrow', 'bin', 'sparrow')
TOTAL_NODES_TOK = '# DUG nodes  : '
SLICED_NODES_TOK = '# Sliced nodes : '
TOTAL_LINES_TOK = '# DUG lines  : '
SLICED_LINES_TOK = '# Sliced lines : '
SLICED_FUNS_TOK = '# Sliced funcs : '
RESULT = [[
    'target', 'poc', 'total_nodes', 'sliced_nodes', 'total_lines',
    'sliced_lines', 'sliced_functions'
]]


import datetime

sa_time = []

def save_satime(prog, binname, cve, step2_start_time, step2_end_time):
    sa_time.append(["DAFL", prog, binname, cve, 
                    step2_start_time.timestamp(), step2_end_time.timestamp(), (step2_end_time - step2_start_time).total_seconds()])

def write_satime_csv():
    with open('/sa_time_DAFL.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(sa_time)


def read_file(filename):
    f = open(filename, "r")
    buf = f.read().strip()
    f.close()
    return buf


def run_sparrow(works, thin):
    PROCS=[]
    for prog in works:
        start_time = datetime.datetime.now()
        
        input_dir = os.path.join(SMAKE_OUT_DIR, prog)
        input_files = glob.glob(input_dir + '/*.i')

        out_dir = os.path.join(SPARROW_OUT_DIR, prog)
        shutil.rmtree(out_dir, ignore_errors=True)
        os.makedirs(out_dir)
        cmd=[
            SPARROW_PATH, "-outdir", out_dir,
            "-frontend", SLICE_TARGETS[prog]['frontend'],
            "-unsound_alloc",
            "-unsound_const_string",
            "-unsound_recursion",
            "-unsound_noreturn_function",
            "-unsound_skip_global_array_init", "1000",
            "-skip_main_analysis", "-cut_cyclic_call",
            "-unwrap_alloc",
            "-entry_point", SLICE_TARGETS[prog]['entry_point'],
            "-max_pre_iter", "10"
        ]
        
        if thin:
            INPUT_DIR = DAFL_INPUT_DIR
        else:
            INPUT_DIR = DAFL_NAIVE_INPUT_DIR
            cmd += ["-full_slice"]

        bugs = SLICE_TARGETS[prog]['bugs']
        cmd_0 = cmd.copy()
        for bug in bugs:
            if os.path.exists(os.path.join(TARG_LOC_DIR, prog, bug+".sparrow")):
                slice_loc = read_file(os.path.join(TARG_LOC_DIR, prog, bug+".sparrow"))
            else:
                slice_loc = read_file(os.path.join(TARG_LOC_DIR, prog, bug))
            cmd = cmd_0 + ["-slice", bug + "=" + slice_loc]
            if 'additional_opt' in SLICE_TARGETS[prog]:
                cmd += SLICE_TARGETS[prog]['additional_opt']
            cmd += input_files

            run_sparrow = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            proc_obj = {
                "prog": prog,
                "p": run_sparrow,
                "outdir": out_dir,
                "start_time": start_time,
                "bug": bug
            }
            PROCS.append(proc_obj)

    for proc in PROCS:
        prog = proc["prog"]
        proc["p"].communicate()

        bug = proc["bug"]            
        # First, copy instrumentation target file.
        dst_dir = os.path.join(INPUT_DIR, "inst-targ", prog)
        os.makedirs(dst_dir, exist_ok=True)
        inst_targ_file = os.path.join(proc["outdir"], bug, "slice_func.txt")
        copy_cmd = "cp %s %s" % (inst_targ_file, os.path.join(dst_dir, bug))
        run_cmd(copy_cmd)
        # Now, copy DFG information file.
        dst_dir = os.path.join(INPUT_DIR, "dfg", prog)
        os.makedirs(dst_dir, exist_ok=True)
        dfg_file = os.path.join(proc["outdir"], bug, "slice_dfg.txt")
        copy_cmd = "cp %s %s" % (dfg_file, os.path.join(dst_dir, bug))
        run_cmd(copy_cmd)
        end_time = datetime.datetime.now()
        save_satime(prog, bug, bug, proc["start_time"], end_time)
            

def main():

    if len(sys.argv) != 3:
        print("Usage: %s <benchmark> <thin/naive>" % sys.argv[0])
        exit(1)
    benchmark = sys.argv[1]
    thin = True if sys.argv[2] == "thin" else False
    worklist = generate_slicing_worklist(benchmark)

    os.makedirs(SPARROW_OUT_DIR, exist_ok=True)
    while len(worklist) > 0:
        works = fetch_works(worklist)
        run_sparrow(works, thin)
    shutil.rmtree(SPARROW_OUT_DIR, ignore_errors=True)
    
    write_satime_csv()


if __name__ == '__main__':
    main()
