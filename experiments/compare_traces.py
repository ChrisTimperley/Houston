#!/usr/bin/env python3
import argparse

import houston

DESCRIPTION = """
Compares two sets of traces, generated using the same mission, to determine
whether there is a significant difference between them (i.e., does the robot
appear to behave differently?).
""".strip()


def parse_args():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('file1', type=str, help='path to a trace file.')
    p.add_argument('file2', type=str, help='path to a trace file.')
    return p.parse_args()


def main():
    args = parse_args()


if __name__ == '__main__':
    main()
