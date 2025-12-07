#!/bin/bash

while true; do
    claude --dangerously-skip-permissions

    echo -n "Would you like it to resume? Y/N: "
    read answer

    case "$answer" in
        Y|y)
            claude --dangerously-skip-permissions <<EOF
resume
EOF
            ;;
        N|n)
            echo "Not resuming. Exiting."
            exit 0
            ;;
        *)
            echo "Invalid input. Exiting."
            exit 1
            ;;
    esac
done
