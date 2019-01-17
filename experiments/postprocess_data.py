import subprocess

import os
import json
import csv

import argparse

def setup_arg_parser():
    parser = argparse.ArgumentParser(description='Posprocess data')
    parser.add_argument('files', type=str, action='store',
                       help='txt file containing ordered list of files to process.')
    parser.add_argument('--output-dir', action='store', type=str,
                        default='GBDT-data/',
                        help='the directory where the results will be stored')
    args = parser.parse_args()
    return args


def transform_data(files_filename, output_dir):
    data_filename = os.path.join(output_dir, 'data.csv.gz')
    meta_filename = os.path.join(output_dir, '_meta.txt')
    files = []
    with open(files_filename, 'r') as f:
        for row in f:
            files.append(row.strip())

    heads = []
    index = 1
    for filename in files:
        result = subprocess.check_output("wc -l {}".format(filename), shell=True).decode().strip()
        linecount = int(result.split(' ')[0])
        heads.append(str(index))
        if index == 1:
            os.system("cp {} {}".format(filename, data_filename))
        else:
            os.system("tail -n {} {} >> {}".format(linecount-1, filename, data_filename))
        index += linecount - 1

    assert len(heads) == len(files)
    with open(meta_filename, 'w') as f:
        f.write(",".join(heads))

if __name__=="__main__":
    args = setup_arg_parser()
    transform_data(args.files, args.output_dir)
