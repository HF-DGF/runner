import sys, os, time, csv, shutil
from common import MAX_INSTANCE_NUM, run_cmd, run_cmd_in_docker, check_cpu_count, fetch_works, MEM_PER_INSTANCE
from benchmark import HFDGF_EARLY_FUCK_FUZZ_TARGETS, generate_fuzzing_worklist, ALL_CANNOT_TARGETS, HFDGF_FUZZ_TARGETS, ALL_FUZZ_TARGETS, HFDGF_OTHER_TARGETS
from parse_result import print_result
from plot import draw_result

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
IMAGE_NAME = "HFDGF-runner:abalation"
SUPPORTED_TOOLS = \
  ["HFDGF", "HFDGF_noasan", 
   "AFL", "AFLGo", "Beacon", "WindRanger",
   "DAFL", "DAFL_noasan" ]


def decide_outdir(target, timelimit, iteration, tool):
    name = "%s-%ssec-%siters" % (target, timelimit, iteration)
    if target == "origin":
        outdir = os.path.join(BASE_DIR, "output", "origin")
    elif tool == "":
        outdir = os.path.join(BASE_DIR, "output", name)
    else:
        outdir = os.path.join(BASE_DIR, "output", name, tool)
    os.makedirs(outdir, exist_ok=True)
    return outdir


def decide_outdir_tool(name, tool):
    if tool == "":
        outdir = os.path.join(name)
    else:
        outdir = os.path.join(name, tool)
    os.makedirs(outdir, exist_ok=True)
    return outdir


def spawn_containers(works):
    for i in range(len(works)):
        tool, targ_prog, _, _, iter_id = works[i]
        cmd = "docker run --tmpfs /box:exec --rm -m=%dg --cpuset-cpus=%d -it -d --name %s-%s-%s %s" \
                % (MEM_PER_INSTANCE, i, tool, targ_prog, iter_id, IMAGE_NAME)
        run_cmd(cmd)


def run_fuzzing(works, timelimit):
    for (tool, targ_prog, cmdline, src, iter_id) in works:
        cmd = "/tool-script/run_%s.sh %s \"%s\" %s %d" % \
                (tool, targ_prog, cmdline, src, timelimit)
        run_cmd_in_docker("%s-%s-%s" % (tool, targ_prog, iter_id), cmd, True)


def wait_finish(works, timelimit):
    time.sleep(timelimit)
    total_count = len(works)
    elapsed_min = 0
    while True:
        if elapsed_min > 120:
            break
        time.sleep(60)
        elapsed_min += 1
        print("Waited for %d min" % elapsed_min)
        finished_count = 0
        for (tool, targ_prog, _, _, iter_id) in works:
            container = "%s-%s-%s" % (tool, targ_prog, iter_id)
            stat_str = run_cmd_in_docker(container, "cat /STATUS", False)
            if "FINISHED" in stat_str:
                finished_count += 1
            else:
                print("%s-%s-%s not finished" % (tool, targ_prog, iter_id))
        if finished_count == total_count:
            print("All works finished!")
            break


def store_outputs(works, name):
    for (tool, targ_prog, cmdline, src, iter_id) in works:
        outdir = decide_outdir_tool(name, tool)
        container = "%s-%s-%s" % (tool, targ_prog, iter_id)
        cmd = "docker cp %s:/output %s/%s" % (container, outdir, container)
        run_cmd(cmd)


def cleanup_containers(works):
    for (tool, targ_prog, _, _, iter_id) in works:
        cmd = "docker kill %s-%s-%s" % (tool, targ_prog, iter_id)
        run_cmd(cmd)


def main():
    if len(sys.argv) < 4:
        print("Usage: %s <run/parse> <table/figure/target name> <time> <iterations> \"<tool list>\" " % sys.argv[0])
        exit(1)

    check_cpu_count()

    action = sys.argv[1]
    if action not in ["run", "parse", "getresult"]:
        print("Invalid action! Choose from [run, parse]" )
        exit(1)

    target = sys.argv[2]
    timelimit = int(sys.argv[3])
    iteration = int(sys.argv[4])
    target_list = ""
    tools_to_run = tools = []
    
    match target:
        case "HFDGF":
            benchmark = "HFDGFtarget"
            target_list = [x for (x,y,z,w) in HFDGF_FUZZ_TARGETS]
            tools += ["HFDGF"]
        case "HFDGFother":
            benchmark = "HFDGFothertarget"
            target_list = [x for (x,y,z,w) in HFDGF_OTHER_TARGETS]
            tools += ["AFL", "AFLGo", "WindRanger", "DAFL", "Beacon", "HFDGF", "HFDGF_noasan"]
        case "earlyfuck":
            benchmark = "HFDGFearlyfucktarget"
            target_list = [x for (x,y,z,w) in HFDGF_EARLY_FUCK_FUZZ_TARGETS]
            tools += ["HFDGF"]
        case "cannot":
            benchmark = "cannottarget"
            target_list = [x for (x,y,z,w) in ALL_CANNOT_TARGETS]
            tools += ["AFL", "HFDGF", "AFLGo", "WindRanger", "DAFL"]
        case "noasan":
            benchmark = "HFDGFtarget"
            target_list = [x for (x,y,z,w) in HFDGF_FUZZ_TARGETS]
            tools += ["HFDGF_noasan", "Beacon", "DAFL_noasan"]
        case "all":
            benchmark = "all"
            target_list = [x for (x,y,z,w) in ALL_FUZZ_TARGETS]
            tools += ["AFL", "HFDGF", "AFLGo", "WindRanger", "DAFL"]
        case _:
            if target in [x for (x,y,z,w) in ALL_FUZZ_TARGETS]:
                benchmark = target
                target_list = [target]
                if len(sys.argv) == 6:
                    tools += sys.argv[5].split()
                    if not all([x in SUPPORTED_TOOLS for x in tools]):
                        print("Invalid tool in the list! Choose from %s" % SUPPORTED_TOOLS)
                        exit(1)
                else:
                    tools += SUPPORTED_TOOLS
            else:
                print("Invalid target!")


    ### 1. Run fuzzing
    if action == "run":
        # 输出预计时间
        total_hours = (len(tools) * len(target_list) * timelimit * iteration) / (60 * 60) / MAX_INSTANCE_NUM

        print("工具数量：%d" % len(tools))
        print("漏洞数量：%d" % len(target_list))
        print("迭代次数：%d" % iteration)
        print("单次时长：%d 分钟" % (timelimit/60))
        
        print("预计消耗时长：%.2f小时" % total_hours)
        print("预计消耗时长：%.2f天" % (total_hours / 24))
        
        worklist = []
        for tool in tools_to_run:
            worklist.extend(generate_fuzzing_worklist(tool, benchmark, iteration))
        
        cleanup_containers(worklist)
        while len(worklist) > 0:
            works = fetch_works(worklist)

            spawn_containers(works)
            run_fuzzing(works, timelimit)
            wait_finish(works, timelimit)

            name = decide_outdir(target, str(timelimit), str(iteration), "")
            store_outputs(works, name)
            cleanup_containers(works)
            
            #### Reset timelimit to user input
            timelimit = int(sys.argv[3])


    if "origin" in sys.argv[2]:
        outdir = decide_outdir("origin", "", "", "")
    else:
        outdir = decide_outdir(target, str(timelimit), str(iteration), "")
    
    ### 2. Parse and print results in CSV and TSV format
    print_result(outdir, target, target_list, timelimit,  iteration, tools)

    ### 3. Draw bar plot with TSV file
    draw_result(outdir, target)


if __name__ == "__main__":
    main()
