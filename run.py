import argparse
import os
# ./build/factgen-exe --out-dir  mini-cclyzerpp/bc-facts/ --context-sensitivity insensitive psql.bc
# souffle --fact-dir mini-cclyzerpp/bc-facts --output-dir mini-cclyzerpp/benchmark-input datalog/benchmark_setup.project  
# souffle --fact-dir mini-cclyzerpp/benchmark-input mini-cclyzerpp/main.dl
EGGLOG_PATH = "./egg-smol/target/release/egg-smol "
FACT_GEN = "./cclyzerpp/build/factgen-exe "

def build_cclyzerpp():
    code = os.system("figlet -k building cclyzer++")
    code |= os.system("cd cclyzerpp && cmake -G Ninja -B build -S .")
    code |= os.system("cd cclyzerpp && cmake --build build -j $(nproc) --target factgen-exe")
    return code == 0

def build_egglog():
    code = os.system("figlet -k building egglog")
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
            # souffle --fact-dir mini-cclyzerpp/bc-facts --output-dir mini-cclyzerpp/benchmark-input datalog/benchmark_setup.project  


parser = argparse.ArgumentParser(description='Benchmarking egglog on the pointer analysis benchmark')
parser.add_argument("--build-cclyzerpp", action='store_true')
parser.add_argument("--build-egglog", action='store_true')

args = parser.parse_args()

if args.build_cclyzerpp and not build_cclyzerpp():
    print("build cclyzer failed")
    exit(1)

if args.build_egglog and not build_egglog():
    print("build egglgo failed")
    exit(1)

# gen_facts_from_bc()
gen_benchmark_inputs()