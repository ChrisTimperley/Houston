## How to run the experiments

1. You first start by generating a set of missions:
   ```
   python experiments/generate_missions.py <number_of_mission> <max_num_commands> [--output_file OUTPUT_FILE] [--seed SEED]
   ```
   Example:
   ```
   python experiments/generate_missions.py 500 10 --output_file missions.json
   ```

2. Then you need to collect traces for these missions:
   ```
   python experiments/build_traces.py <snapshot> <missions> <output> [--verbose] [--repeats REPEATS] [--threads THREADS] [--kill-container]
   ```
   Example:
   ```
   python experiments/build_traces.py arducopter:3.6.4 missions.json traces/ --threads 5 --verbose
   ```

3. After all traces are collected you can start building the model. First, you need to preprocess data to prepare it for clustering:
   ```
   python experiments/preprocess_data.py <traces> [--ignore-cat] [--output-dir OUTPUT_DIR]
   ```
   Example:
   ```
   python experiments/preprocess_data.py traces/ --ignore-cat --output-dir out/
   ```
   This script will create a `.csv` file for each command in traces and the name of the file specifies which command and which trace it belongs to.

4. The data produced in the previous step will be used by `experiments/clustering.R` to apply `dynamic time warping (dtw)` clustering on a specific command:
   ```
   Rscript --vanilla experiments/clustering.R --data_dir <DATA_DIR> -c <COMMAND> [--output_dir OUTPUT_DIR] [-n DP_NUM] [-k CLUSTERS] [--fuzzy]
   ```
   Example:
   ```
   Rscript --vanilla experiments/clustering.R --data_dir out/ -c MAV_CMD_NAV_TAKEOFF --output_dir clusters/ -n 20 -k 3
   ```
   This script will put commands in `k` clusters and output 4 files:
   1. `COMMAND_files.txt`: the files included in clustering.
   2. `COMMAND_labels.txt`: the labels (clusters) for each file (has the same order as previous file).
   3. `COMMAND.RData`: the R cluster model stored.
   4. `COMMAND.pdf`: the plot of clusters.

   For this script you need to have two R packages already installed: `dtwclust` and `optparse`. If you have not installed them, simply open an R interactive session and type the followings:
   ```
   > install.packages("dtwclust")
   > install.packages("optparse")
   ```

5. If you want to apply Grammar-Based Decision Tree (GBDT) to the data, you need a postprocessing step to prepare the data:
   ```
   python experiments/postprocess_data.py <files> [--output-dir OUTPUT_DIR]
   ```
   Example:
   ```
   python experiments/postprocess_data clusters/MAV_CMD_NAV_TAKEOFF_files.txt --output-dir GBDT-out/
   ```
   This script will create two files:
   1. `data.csv.gz`: the csv of all traces of a command concatenated.
   2. `_meta.txt`: the index of the beginning of each separate trace in the previous file.
   These two files along with the labels file from previous step will be the data to the next step. This format is specified by the `MultiVariateTimeSeries` libarary in `julia`.

6. To apply GBDT on the data first clone the project from `https://github.com/afsafzal/GBDTs.jl`:
   ```
   git clone git@github.com:afsafzal/GBDTs.jl.git
   ```
   Install all dependencies specified in the README and run the script as specified:
   ```
   julia learn.jl <path-to-data-dir> <fuzzy-or-normal> <max-depth> [path-to-output-dir]
   ```
