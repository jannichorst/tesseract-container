#!/bin/sh

# Navigate to the directory of this script
SCRIPT_DIR=$(dirname "$0")

# Execute build script
sh "$SCRIPT_DIR/build.sh"

# Execute run script
sh "$SCRIPT_DIR/run.sh"
