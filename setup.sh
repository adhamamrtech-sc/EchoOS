#!/usr/bin/env bash
set -e
sudo apt update
sudo apt install -y git python3-venv python3-pip ffmpeg libportaudio2 portaudio19-dev alsa-utils pulseaudio-utils
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
