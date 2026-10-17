"""One entry point. Run from any directory; outputs are rooted at this project."""
import argparse
import subprocess
import sys
import time
from src.common import ROOT,save_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--generate',action='store_true',help='Generate or replace synthetic raw partitions first.')
    parser.add_argument('--notebooks',action='store_true',help='Create and execute all notebooks.')
    args=parser.parse_args()
    stages=(['generate_data'] if args.generate else [])+['validate_data','build_database','build_metrics','analyse_experiment','create_charts','build_documentation']
    if args.notebooks:stages+=['build_notebooks']
    runtimes=[]
    for stage in stages:
        start=time.perf_counter()
        subprocess.run([sys.executable,'-m',f'src.{stage}'],cwd=ROOT,check=True)
        runtimes.append({'stage':stage,'seconds':round(time.perf_counter()-start,3)})
    save_json('reports/run_timings.json',runtimes)
    print('Pipeline complete.')

if __name__=='__main__':main()
