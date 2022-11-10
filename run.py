import statistics
import argparse
import os
from timeit import default_timer as timer
import matplotlib.pyplot as plt
import numpy as np
import csv

# NOTE that we are only comparing against souffle interpreter mode single thread

DEFAULT_EGGLOG_DIR = "./egg-smol/"
FACT_GEN = "./cclyzerpp/build/factgen-exe "
TIME_OUT = "20s"

parser = argparse.ArgumentParser(description='Benchmarking egglog on the pointer analysis benchmark')
parser.add_argument("--egglog-path", default=DEFAULT_EGGLOG_DIR)
parser.add_argument("--build-cclyzerpp", action='store_true')
parser.add_argument("--build-egglog", action='store_true')
parser.add_argument("--generate-bitcode-facts", action='store_true')
parser.add_argument("--generate-benchmark-inputs", action='store_true')
parser.add_argument("--generate-benchmark-inputs-for", action='store')
parser.add_argument("--read-data-from-cached", action='store_true')
parser.add_argument("--ignore-less-than-second", action='store_true')
parser.add_argument("--no-viz", action='store_true')
parser.add_argument("--run-benchmark", action='store')
parser.add_argument("--no-run", action='store_true')

parser.add_argument("--disable-naive", action='store_true')
parser.add_argument("--disable-sound", action='store_true')
parser.add_argument("--disable-buggy", action='store_true')

args = parser.parse_args()

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

def build_egglog(args):
    shout("building egglog")
    code = 0
    code |= os.system(f"cd {args.egglog_path} && cargo build --release")
    return code == 0

BENCHMARK_SETS = [
    # 'coreutils-8.24', 
    'postgresql-9.5.2'
]
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

def compile_cclyzerpp():
    print("compiling cclyzer++...")
    COMPILE_SOUFFLE = f"souffle -g benchmark_setup benchmark_setup.project && souffle-compile benchmark_setup.cpp"
    if os.system(COMPILE_SOUFFLE) != 0:
        print("compiling cclyzer++ failed. Aborting.")
        exit(1)

def gen_benchmark_input_for(benchmark_set, benchmark_name, compile=False):
    fact_dir = f"bc-facts/{benchmark_set}/{benchmark_name}"
    benchmark_input_dir = f"benchmark-input/{benchmark_set}/{benchmark_name}"
    if os.path.isfile(fact_dir):
        return
    os.system(f"mkdir -p {benchmark_input_dir}")
    command = None
    if compile:
        command = f"./benchmark_setup -F {fact_dir} -D {benchmark_input_dir}"
    else:
        command = f"souffle benchmark_setup.project -F {fact_dir} -D {benchmark_input_dir}"
    print(command)
    if os.system(command) != 0:
        print("error when generating benchmark inputs")
        exit(1)

def gen_benchmark_inputs():
    # compile_cclyzerpp()
    for benchmark_set in BENCHMARK_SETS:
        fact_parent_dir = f"bc-facts/{benchmark_set}"
        for benchmark_name in os.listdir(fact_parent_dir):
            gen_benchmark_input_for(benchmark_set, benchmark_name, False)

with open("main.egg") as f:
    MAIN_EGGLOG_CODE = f.read()

def run_benchmark(args, benchmark_set, benchmark_name):
    print(f"running {benchmark_set}/{benchmark_name}")
    souffle_baselines = [
        ("naive-cclyzerpp.dl", args.disable_naive),
        ("sound-cclyzerpp.dl", args.disable_sound),
        ("mini-cclyzerpp.dl", args.disable_buggy),
    ]
    input_dir = f"benchmark-input/{benchmark_set}/{benchmark_name}"
    times = []
    for (filename, disabled) in souffle_baselines:
        command = f"timeout {TIME_OUT} souffle -F {input_dir} {filename}"
        if disabled:
            times.append(0)
        else:
            souffle_start_time = timer()
            os.system(command)
            souffle_end_time = timer()
            times.append(souffle_end_time - souffle_start_time)

    # egglog without seminaive
    command = f"{args.egglog_path}/target/release/egg-smol main.egg --naive -F {input_dir} > /dev/null 2> /dev/null"
    print(f"Running {command}")
    egglog_start_time = timer()
    if os.system(command) != 0 :
        print("error when run egglog on benchmarks")
        exit(1)
    egglog_end_time = timer()
    times.append(egglog_end_time - egglog_start_time)

    # egglog with seminaive
    command = f"{args.egglog_path}/target/release/egg-smol main.egg -F {input_dir} > /dev/null 2> /dev/null"
    print(f"Running {command}")
    egglog_start_time = timer()
    if os.system(command) != 0 :
        print("error when run egglog on benchmarks")
        exit(1)
    egglog_end_time = timer()
    times.append(egglog_end_time - egglog_start_time)
    print(f"souffle takes time {times[0:3]}, egglog takes time {times[3]}")
    return times

def run_all_benchmarks(args):
    data = []
    for benchmark_set in BENCHMARK_SETS:
        benchmark_parent_dir = f"benchmark-input/{benchmark_set}"
        for benchmark_name in os.listdir(benchmark_parent_dir):
            times = run_benchmark(args, benchmark_set, benchmark_name)
            data.append([
                f"{benchmark_set}/{benchmark_name}",
                times[0],
                times[1],
                times[2],
                times[3],
                times[4],
            ])
    return data

if args.build_cclyzerpp and not build_cclyzerpp():
    print("build cclyzer failed")
    exit(1)

if args.build_egglog and not build_egglog(args):
    print("build egglog failed")
    exit(1)

if args.generate_bitcode_facts:
    gen_facts_from_bc()

if args.generate_benchmark_inputs:
    gen_benchmark_inputs()

if args.generate_benchmark_inputs_for is not None:
    benchmark = args.generate_benchmark_inputs_for
    benchmark_set, benchmark_name = benchmark.split('/')
    gen_benchmark_input_for(benchmark_set, benchmark_name)
    exit()

if args.no_run:
    exit()

if args.run_benchmark is not None:
    benchmark = args.run_benchmark
    benchmark_set, benchmark_name = benchmark.split('/')
    run_benchmark(args, benchmark_set, benchmark_name)
    exit()

data = []

if args.read_data_from_cached:
    with open('benchmark_results.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            data.append((row[0], float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
else:
    data = run_all_benchmarks(args)

    with open('benchmark_results.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for i in range(len(data)):
            writer.writerow(data[i])

hm1 = statistics.harmonic_mean([_patched / _egglog for (_, _naive, _patched, _cclyzerpp, _egglognaive, _egglog) in data])
hm2 = statistics.harmonic_mean([_cclyzerpp / _egglog for (_, _naive, _patched, _cclyzerpp, _egglognaive, _egglog) in data])
hm3 = statistics.harmonic_mean([_egglognaive / _egglog for (_, _naive, _patched, _cclyzerpp, _egglognaive, _egglog) in data])
total = sum([e for (_, _naive, _buggy, _, _, e) in data]) / sum([s for (_, _naive, _buggy, s, _, _) in data])
print(f"Harmonic egglog/patched:     {hm1}")
print(f"Harmonic egglog/cclyzerpp:   {hm2}")
print(f"Harmonic egglog/egglognaive: {hm3}")
print(f"Total egglog/souffle: {total}")

if args.ignore_less_than_second:
    # ignore naive, since it's most likely to timeout
    data = list(filter(lambda x: x[2] >= 1 or x[3] >= 1 or x[4] >= 1 or x[5] >= 1, data))
data = sorted(data, key=lambda x: x[2])
benchmark_full_names = list(map(lambda x: x[0], data))
benchmark_full_names = list(map(lambda x: x.split('/')[1][:-3], benchmark_full_names))

run_times = [list(map(lambda x: 0 if x[i] > 19.5 else x[i], data)) for i in range(1, 6)]
# 0: naive
# 1: patched
# 2: cclyzerpp
# 3: egglog-naive
# 4: egglog

x = np.arange(len(benchmark_full_names))  # the label locations
width = 0.2  # the width of the bars

fig, ax = plt.subplots()
ax.set_yscale('log')
rects1 = ax.bar(x - width - width/2, run_times[0], width, label='eqrel')
rects2 = ax.bar(x - width/2, run_times[1], width, label='patched')
rects3 = ax.bar(x + width/2, run_times[2], width, label='cclyzerpp')
rects4 = ax.bar(x + width + width/2, run_times[3], width, label='EqLog-naive')
rects5 = ax.bar(x + 2 * width + width/2, run_times[4], width, label='EqLog')

ax.set_ylabel('Time (s)')
ax.set_title('Run time of cclyzer++ and EqLog')
ax.set_xticks(x, benchmark_full_names, rotation='vertical')
ax.legend()

# ax.bar_label(rects1, padding=3)
# ax.bar_label(rects2, padding=3)

fig.tight_layout()
plt.savefig('plot.pdf')

if not args.no_viz:
    plt.show()

