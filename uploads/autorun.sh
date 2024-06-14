#!/bin/sh

~/isaacsim.sh --cmd="bash uploads/pass-creds-to-container.sh ; apt-get update && apt-get install -y vim ffmpeg && /isaac-sim/kit/kit /isaac-sim/apps/omni.isaac.sim.kit --ext-folder /isaac-sim/apps --allow-root"