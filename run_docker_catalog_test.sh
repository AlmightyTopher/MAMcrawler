#!/bin/bash

echo "======================================================================"
echo "AUDIOBOOK CATALOG CRAWLER - DOCKER TEST"
echo "======================================================================"
echo

echo "[1/3] Building Docker image..."
docker-compose -f docker-compose.catalog.yml build

if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed!"
    exit 1
fi

echo
echo "[2/3] Running comprehensive test..."
docker-compose -f docker-compose.catalog.yml up

if [ $? -ne 0 ]; then
    echo "ERROR: Test execution failed!"
    exit 1
fi

echo
echo "[3/3] Viewing results..."
echo
echo "Test results saved to:"
echo "- catalog_test_results/"
echo
ls -1 catalog_test_results/*.json 2>/dev/null || echo "No JSON files found"
ls -1 catalog_test_results/*.csv 2>/dev/null || echo "No CSV files found"
ls -1 catalog_test_results/*.md 2>/dev/null || echo "No Markdown files found"
echo

echo "======================================================================"
echo "TEST COMPLETE"
echo "======================================================================"
echo
echo "View reports in: catalog_test_results/"
echo "View logs: audiobook_catalog_test.log"
echo "View screenshots: catalog_cache/*.png"
echo
