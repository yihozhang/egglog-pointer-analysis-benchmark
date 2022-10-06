import argparse
import os
# ./build/factgen-exe --out-dir  mini-cclyzerpp/bc-facts/ --context-sensitivity insensitive psql.bc
# souffle --fact-dir mini-cclyzerpp/bc-facts --output-dir mini-cclyzerpp/benchmark-input datalog/benchmark_setup.project  
# souffle --fact-dir mini-cclyzerpp/benchmark-input mini-cclyzerpp/main.dl
EGGLOG_PATH = "./egg-smol/target/release/egg-smol "

def build_cclyzerpp():
    code = os.system("figlet -k building cclyzer++")
    code |= os.system("cd cclyzerpp && cmake -G Ninja -B build -S .")
    code |= os.system("cd cclyzerpp && cmake --build build -j $(nproc) --target factgen-exe")
    return code == 0

def build_egglog():
    code = os.system("figlet -k building egglog")
    code |= os.system("cd egg-smol && cargo build --release")
    return code == 0

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