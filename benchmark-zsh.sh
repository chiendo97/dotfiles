#!/bin/bash

# Number of times to run the benchmark
runs=10

# Function to get current time in milliseconds
get_time_ms() {
    perl -MTime::HiRes=time -e 'printf "%.0f\n", time * 1000'
}

# Array to store results
declare -a results

echo "Benchmarking zsh startup time for $runs runs..."

for ((i=1; i<=$runs; i++))
do
    start=$(get_time_ms)
    
    # Start zsh and exit immediately
    zsh -i -c exit
    
    end=$(get_time_ms)
    
    # Calculate the difference
    diff=$((end - start))
    
    # Store the result
    results+=($diff)
    
    echo "Run $i: $diff ms"
done

# Calculate and print average
sum=0
for time in "${results[@]}"
do
    sum=$((sum + time))
done

average=$((sum / runs))
echo "Average startup time: $average ms"

