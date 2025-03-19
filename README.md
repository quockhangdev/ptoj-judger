# Putong OJ - Judger

![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)
[![Test Status](https://img.shields.io/github/actions/workflow/status/net-escape/ptoj-judger/ci.yml?label=test)](https://github.com/net-escape/ptoj-judger/actions/workflows/ci.yml)
[![Codecov](https://img.shields.io/codecov/c/github/net-escape/ptoj-judger/main)](https://app.codecov.io/github/net-escape/ptoj-judger)
[![GitHub License](https://img.shields.io/github/license/net-escape/ptoj-judger)](https://github.com/net-escape/ptoj-judger/blob/main/LICENSE)

The next generation [Putong OJ](https://github.com/acm309/PutongOJ) judger 
work with [go-judge](https://github.com/criyle/go-judge) sandbox.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
docker build -t go-judge -f Dockerfile.sandbox .
docker build -t ptoj-judger -f Dockerfile.judger .
```

```bash
docker run -it --privileged -p 5050:5050 -d go-judge
```

See [example.py](example.py) and [main.py](main.py) for more details.

## Test

```bash
pytest --cov=judger
```

See [tests](tests) for more details.
