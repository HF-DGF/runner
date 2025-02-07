import sys, os

import pandas as pd
from common import check_cpu_count, fetch_works, run_cmd
from benchmark import HFDGF_EARLY_SCALE_FUZZ_TARGETS
from parse_result import calc_avg_bitmap_cvg, calc_min_max_tte, median_tte, parse_bitmap_cvg, parse_tte, print_result
from reproduce import cleanup_containers, run_fuzzing, store_outputs, wait_finish

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
IMAGE_NAME = "HFDGF-runner:earlyfuck"
TOOLS = ["HFDGF"]
MEM_PER_INSTANCE=54

OUTPUT_DIR = os.path.join(BASE_DIR, "output", "earlyfuck")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def spawn_containers(works):
    for i in range(len(works)):
        tool, targ_prog, _, _, iter_id = works[i]
        cmd = "docker run --tmpfs /box:exec --rm -m=%dg --cpuset-cpus=%d -it -d --name %s-%s-%s %s" \
                % (MEM_PER_INSTANCE, i, tool, targ_prog, iter_id, IMAGE_NAME)
        run_cmd(cmd)


def get_timelimit(targ):
    for tl, targets in HFDGF_EARLY_SCALE_FUZZ_TARGETS.items():
        if targ in [x[0] for x in targets]:
            return tl

def get_iter_count(targ):
    match get_timelimit(targ):
        case 3600: #  5个
            return 20
        case 86400: # 6 个
            return 9
        case _:
            return 1


def parse_result():
    targ_list = [x for y in HFDGF_EARLY_SCALE_FUZZ_TARGETS.values() for (x,_,_,_) in y]
    
    med_df_dict = {}
    med_df_dict["Target"] = targ_list
    
    all_df_dict = {}
    all_df_dict["Target"] = targ_list
    
    min_max_df_dict = {}
    min_max_df_dict["Target"] = targ_list
    
    avg_bitmap_cvg_dict = {}
    avg_bitmap_cvg_dict["Target"] = targ_list

    # sa_dict = read_sa_results()
    for tool in TOOLS:
        med_tte_list = []
        all_tte_list = []
        min_max_tte_list = []
        avg_bitmap_cvg_list = []
        for targ in targ_list:
            tte_list = []
            bitmap_cvg_list = []

            iter_cnt = get_iter_count(targ)
            for iter_id in range(iter_cnt):
                targ_dir = os.path.join(OUTPUT_DIR, tool, "%s-%s-iter-%d" % (tool, targ, iter_id))
                tte = parse_tte(targ, targ_dir)
                tte_list.append(tte)

                # record this iter bitmap coverage
                bitmap_cvg = parse_bitmap_cvg(targ_dir)
                bitmap_cvg_list.append(bitmap_cvg)

            tl = get_timelimit(targ)

            all_tte_list.append(tte_list)
            med_tte = median_tte(tte_list, tl)
            min_max_tte = calc_min_max_tte(tte_list, tl)
            if ">" in med_tte:
                found_iter_cnt = iter_cnt - len([x for x in tte_list if (x is None or x > tl)])
                med_tte = "N.A.(%d/%d)" % (found_iter_cnt, iter_cnt)
            
            med_tte_list.append(med_tte)
            min_max_tte_list.append(min_max_tte)
            avg_bitmap_cvg_list.append(calc_avg_bitmap_cvg(bitmap_cvg_list))
        med_df_dict[tool] = med_tte_list
        all_df_dict[tool] = all_tte_list
        min_max_df_dict[tool] = min_max_tte_list
        avg_bitmap_cvg_dict[tool] = avg_bitmap_cvg_list
    
    outdir = OUTPUT_DIR
    exp_id = "abalation"
    med_tte_df = pd.DataFrame.from_dict(med_df_dict)
    med_tte_df.to_csv(os.path.join(outdir, "%s_med.csv" % exp_id), index=False)
    med_tte_df.to_csv(os.path.join(outdir, "%s_med.tsv" % exp_id), index=False, sep="\t")
    
    min_max_tte_df = pd.DataFrame.from_dict(min_max_df_dict)
    min_max_tte_df.to_csv(os.path.join(outdir, "%s_min_max.csv" % exp_id), index=False)
    min_max_tte_df.to_csv(os.path.join(outdir, "%s_min_max.tsv" % exp_id), index=False, sep="\t")
    
    all_tte_df = pd.DataFrame.from_dict(all_df_dict)
    all_tte_df.to_json(os.path.join(outdir, "%s.json" % exp_id), index=False)
    all_tte_df.to_csv(os.path.join(outdir, "%s.csv" % exp_id), index=False)
    
    bitmap_cvg_df = pd.DataFrame.from_dict(avg_bitmap_cvg_dict)
    bitmap_cvg_df.to_csv(os.path.join(outdir, "%s_bitmap_cvg.csv" % exp_id), index=False)
    bitmap_cvg_df.to_csv(os.path.join(outdir, "%s_bitmap_cvg.tsv" % exp_id), index=False, sep="\t")


def main():
    check_cpu_count()

    for timelimit, targets in HFDGF_EARLY_SCALE_FUZZ_TARGETS.items():
        worklist = []
        for tool in TOOLS:
            for (targ_prog, cmdline, src, _) in targets:
                if src not in ["stdin", "file"]:
                    print("Invalid input source specified: %s" % src)
                    exit(1)
                for i in range(get_iter_count(targ_prog)):
                    iter_id = "iter-%d" % i
                    worklist.append((tool, targ_prog, cmdline, src, iter_id))

        cleanup_containers(worklist)
        while len(worklist) > 0:
            works = fetch_works(worklist)

            spawn_containers(works)
            run_fuzzing(works, timelimit)
            wait_finish(works, timelimit)

            store_outputs(works, OUTPUT_DIR)
            cleanup_containers(works)

        parse_result()


if __name__ == "__main__":
    main()
