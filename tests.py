import os
import subprocess
import csv

dirs=["pj2-tests/sat","pj2-tests/unsat"]
expected=["sat","unsat"]
python_files=["py.py","solve.py"]

columns=['file','our_time_ms','z3_time_ms','correct']
results_file="results.csv"
with open(results_file, mode='w', newline='') as file:
    file.write(";".join(columns)+"\n")

for i,path in enumerate(dirs):
    dir = os.fsencode(path)
    
    for file in os.listdir(dir):
        file_name = os.fsdecode(file)
        file_name=path+'/'+file_name
        results=[]
        times=[]
        
        for j,py in enumerate(python_files):
            out_bytes=subprocess.check_output('python "'+py+'" "'+file_name+'"')
            out=out_bytes.decode().replace("\r\n","\n")
            lines=out.split("\n",1)

            results.append(lines[0])
            pos_ms=0
            try:
                pos_ms=lines[1].index(" ms")
            except ValueError:
                times.append("error")
                continue

            ms=lines[1][:pos_ms]
            if not ms.isdigit():
                raise ValueError(file_name+", "+py+": Time wasn't returned")
            times.append(ms)

        data=[file_name,times[0],times[1],"true" if results[0]==results[1] else "false"]
        with open(results_file, mode='a', newline='') as file:
            file.write(";".join(data)+"\n")