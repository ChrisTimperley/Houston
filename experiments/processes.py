from typing import Tuple
import json

import concurrent.futures

import bugzoo
import bugzoo.server
import houston


def job(bz: bugzoo.Client,
        mission: houston.Mission
        ) -> None:
    print("completed job")


def main(bz: bugzoo.Client,
         missions: Tuple[houston.Mission, ...]
         ) -> None:
    w = 2
    futures = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=w) as e:
        for mission in missions:
            future = e.submit(job, bz, mission)
            futures.append(future)
    concurrent.futures.wait(futures)


if __name__ == '__main__':
    # load a bunch of missions
    with open('missions.json', 'r') as f:
        jsn = json.load(f)
    missions = [houston.Mission.from_dict(d) for d in jsn]

    with bugzoo.server.ephemeral() as bz:
        main(bz, missions)
