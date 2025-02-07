python3 ./scripts/reproduce.py run tbl2-scaled 36000 2


# 运行 HFDGF 一次，
python3 ./scripts/reproduce.py run myfuzzer 36000 1


# kill
docker kill `docker ps --all |grep HFDGF-runner | cut -d " " -f1`
docker rm `docker ps --all |grep HFDGF-runner | cut -d " " -f1`


# 运行大家都跑不出来的目标， 11个都超时的目标
python3 ./scripts/reproduce.py run cannot 86400 1


python3 ./scripts/reproduce.py run HFDGFother 86400 3

