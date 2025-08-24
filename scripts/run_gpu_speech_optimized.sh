#!/bin/bash
# Optimized wrapper script for persistent GPU speech-to-text service

# Set up CUDNN library paths
VENV_PATH="/home/sati/speech-to-text-for-ubuntu/venv"
CUDNN_LIB="$VENV_PATH/lib/python3.10/site-packages/nvidia/cudnn/lib"
CUBLAS_LIB="$VENV_PATH/lib/python3.10/site-packages/nvidia/cublas/lib"

# Export library path
export LD_LIBRARY_PATH="$CUDNN_LIB:$CUBLAS_LIB:$LD_LIBRARY_PATH"

# Log the environment setup
echo "$(date): Optimized GPU Speech wrapper starting" >> /tmp/gpu_wrapper_optimized.log
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> /tmp/gpu_wrapper_optimized.log

# Run the optimized GPU speech script with persistent model
exec "$VENV_PATH/bin/python3" "/home/sati/speech-to-text-for-ubuntu/src/gpu_service_optimized.py" "$@"