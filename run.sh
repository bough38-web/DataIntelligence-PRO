#!/bin/bash

# Move to the script's directory
cd "$(dirname "$0")"

echo "=========================================="
echo "   데이터 통합 병합·추출기 PRO 실행기"
echo "=========================================="

# 1. Virtual environment check
if [ ! -d "venv" ]; then
    echo "[1/3] 가상 환경(venv)을 생성하고 있습니다..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 오류: 가상 환경 생성에 실패했습니다. Python3가 설치되어 있는지 확인해 주세요."
        exit 1
    fi
fi

# 2. Dependency check/install
echo "[2/3] 필요한 라이브러리를 확인 및 설치 중입니다..."
./venv/bin/python3 -m pip install pandas PySide6 openpyxl lxml html5lib beautifulsoup4

if [ $? -ne 0 ]; then
    echo "❌ 오류: 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인해 주세요."
    exit 1
fi

# 3. Run application
echo "[3/3] 프로그램을 실행합니다..."
./venv/bin/python3 -m app.main

if [ $? -ne 0 ]; then
    echo "❌ 프로그램이 비정상 종료되었습니다."
fi
