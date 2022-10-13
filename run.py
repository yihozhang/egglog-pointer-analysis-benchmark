import argparse
import os
from timeit import default_timer as timer
import matplotlib.pyplot as plt
import numpy as np
import csv

# NOTE that we are only comparing against souffle interpreter mode single thread

EGGLOG_PATH = "./egg-smol/target/release/egg-smol "
FACT_GEN = "./cclyzerpp/build/factgen-exe "

def shout(msg):
    bars = "=" * len(msg)
    print(bars)
    print(msg)
    print(bars + '\n')

def build_cclyzerpp():
    shout("building cclyzer++")
    code = 0
    code |= os.system("cd cclyzerpp && cmake -G Ninja -B build -S .")
    code |= os.system("cd cclyzerpp && cmake --build build -j $(nproc) --target factgen-exe")
    return code == 0

def build_egglog():
    shout("building egglog")
    code = 0
    code |= os.system("cd egg-smol && cargo build --release")
    return code == 0

BENCHMARK_SETS = ['coreutils-8.24', 'postgresql-9.5.2']
def gen_facts_from_bc():
    for benchmark_set in BENCHMARK_SETS:
        benchmark_dir = f"benchmarks/{benchmark_set}"
        fact_parent_dir = f"bc-facts/{benchmark_set}"
        for filename in os.listdir(benchmark_dir):
            if not filename.endswith(".bc"):
                continue
            benchmark_file = f"{benchmark_dir}/{filename}"
            fact_dir = f"{fact_parent_dir}/{filename}"
            os.system(f"mkdir -p {fact_dir}")
            command = f"{FACT_GEN} --out-dir {fact_dir} --context-sensitivity insensitive {benchmark_file}"
            print(command)
            if os.system(command) != 0:
                print("error when generating facts from bitcode modules")
                exit(1)

def gen_benchmark_inputs():
    print("compiling cclyzer++...")
    COMPILE_SOUFFLE = f"souffle -g benchmark_setup benchmark_setup.project && souffle-compile benchmark_setup.cpp"
    if os.system(COMPILE_SOUFFLE) != 0:
        print("compiling cclyzer++ failed. Aborting.")
        exit(1)
    for benchmark_set in BENCHMARK_SETS:
        fact_parent_dir = f"bc-facts/{benchmark_set}"
        for benchmark_name in os.listdir(fact_parent_dir):
            fact_dir = f"{fact_parent_dir}/{benchmark_name}"
            benchmark_input_dir = f"benchmark-input/{benchmark_set}/{benchmark_name}"
            if os.path.isfile(fact_dir):
                continue
            os.system(f"mkdir -p {benchmark_input_dir}")
            command = f"./benchmark_setup -F {fact_dir} -D {benchmark_input_dir}"
            print(command)
            if os.system(command) != 0:
                print("error when generating benchmark inputs")
                exit(1)

with open("main.egg") as f:
    MAIN_EGGLOG_CODE = f.read()

def run_benchmark(benchmark_set, benchmark_name):
    input_dir = f"benchmark-input/{benchmark_set}/{benchmark_name}"
    command = f"souffle -F {input_dir} main.dl"
    souffle_start_time = timer()
    if os.system(command) != 0 :
        print("error when run souffle on benchmarks")
        exit(1)
    souffle_end_time = timer()
    souffle_duration = souffle_end_time - souffle_start_time

    command = f"{EGGLOG_PATH} main.egg -F {input_dir} > /dev/null"
    print(f"Running {command}")
    egglog_start_time = timer()
    if os.system(command) != 0 :
        print("error when run egglog on benchmarks")
        exit(1)
    egglog_end_time = timer()
    egglog_duration = egglog_end_time - egglog_start_time
    print(f"souffle takes time {souffle_duration}, egglog takes time {egglog_duration}")
    return (souffle_duration, egglog_duration)

def run_all_benchmarks():
    data = []
    for benchmark_set in BENCHMARK_SETS:
        benchmark_parent_dir = f"benchmark-input/{benchmark_set}"
        for benchmark_name in os.listdir(benchmark_parent_dir):
            time = run_benchmark(benchmark_set, benchmark_name)
            data.append([
                f"{benchmark_set}/{benchmark_name}",
                time[0],
                time[1],
            ])
    return data


parser = argparse.ArgumentParser(description='Benchmarking egglog on the pointer analysis benchmark')
parser.add_argument("--build-cclyzerpp", action='store_true')
parser.add_argument("--build-egglog", action='store_true')
parser.add_argument("--generate-bitcode-facts", action='store_true')
parser.add_argument("--read-data-from-cached", action='store_true')
parser.add_argument("--ignore-less-than-second", action='store_true')
parser.add_argument("--no-viz", action='store_true')
parser.add_argument("--run-benchmark", action='store')
parser.add_argument("--no-run", action='store_true')
args = parser.parse_args()

if args.build_cclyzerpp and not build_cclyzerpp():
    print("build cclyzer failed")
    exit(1)

if args.build_egglog and not build_egglog():
    print("build egglog failed")
    exit(1)

if args.generate_bitcode_facts:
    gen_facts_from_bc()

if args.no_run:
    exit()

if args.run_benchmark is not None:
    benchmark = args.run_benchmark
    benchmark_set, benchmark_name = benchmark.split('/')
    run_benchmark(benchmark_set, benchmark_name)
    exit()

data = []

if args.read_data_from_cached:
    with open('benchmark_results.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            data.append((row[0], float(row[1]), float(row[2])))
else:
    data = run_all_benchmarks()

    with open('benchmark_results.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for i in range(len(data)):
            writer.writerow(data[i])

if args.ignore_less_than_second:
    data = list(filter(lambda x: x[1] >= 1 or x[2] >= 1, data))

benchmark_full_names = list(map(lambda x: x[0], data))
souffle_run_times = list(map(lambda x: x[1], data))
egglog_run_times = list(map(lambda x: x[2], data))

x = np.arange(len(benchmark_full_names))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(x - width/2, souffle_run_times, width, label='Souffle')
rects2 = ax.bar(x + width/2, egglog_run_times, width, label='Egglog')

ax.set_ylabel('Time (s)')
ax.set_title('Run time of cclyzer++ and egglog')
ax.set_xticks(x, benchmark_full_names, rotation='vertical')
ax.legend()

# ax.bar_label(rects1, padding=3)
# ax.bar_label(rects2, padding=3)

fig.tight_layout()
plt.savefig('plot.png')

if not args.no_viz:
    plt.show()

