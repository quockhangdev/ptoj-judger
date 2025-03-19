# Putong OJ - Judger

![Python](https://img.shields.io/badge/python-%3E%3D3.11-3572a5)
[![Test Status](https://img.shields.io/github/actions/workflow/status/net-escape/ptoj-judger/ci.yml?label=test)](https://github.com/net-escape/ptoj-judger/actions/workflows/ci.yml)
[![Codecov](https://img.shields.io/codecov/c/github/net-escape/ptoj-judger/main)](https://app.codecov.io/github/net-escape/ptoj-judger)
[![GitHub License](https://img.shields.io/github/license/net-escape/ptoj-judger)](https://github.com/net-escape/ptoj-judger/blob/main/LICENSE)

This is a Judger for the [Putong OJ](https://github.com/net-escape/ptoj-backend) platform, designed to evaluate submitted code in programming contests and algorithmic problem-solving. It works with the [go-judge](https://github.com/criyle/go-judge) secure sandbox to provide a secure and efficient code execution environment.

## Getting Started 🚀

### Prerequisites

Ensure that you have the [Docker](https://www.docker.com/) installed on your server.

Additionally, you need to have a running instance of [Putong OJ](https://github.com/net-escape/ptoj-backend).

### Build and Run

#### Build Docker Images

Run the following commands to build the necessary Docker images:

```bash
docker build -t ptoj-sandbox -f Dockerfile.sandbox .
docker build -t ptoj-judger -f Dockerfile.judger .
```

#### Run the Judger

Replace `<YOUR_REDIS_URL>` and `<PROBLEM_DATA_PATH>` with your actual configurations:

```yaml
services:
  ptoj-sandbox:
    image: ptoj-sandbox
    volumes:
      - <PROBLEM_DATA_PATH>:/app/data:ro
    privileged: true
    networks:
      - internal

  ptoj-judger:
    image: ptoj-judger
    environment:
      - PTOJ_REDIS_URL=<YOUR_REDIS_URL>
      - PTOJ_SANDBOX_ENDPOINT=http://ptoj-sandbox:5050
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

### Environment Variables

The following environment variables are available for configuration:

| Variable                | Description                  | Default                  |
| ----------------------- | ---------------------------- | ------------------------ |
| `PTOJ_REDIS_URL`        | Redis connection URL         | `redis://localhost:6379` |
| `PTOJ_SANDBOX_ENDPOINT` | Sandbox endpoint URL         | `http://localhost:5050`  |
| `PTOJ_INIT_CONCURRENT`  | Initial concurrent processes | `1`                      |
| `PTOJ_LOG_FILE`         | Log file path                | `judger.log`             |
| `PTOJ_DEBUG`            | Debug mode (0/1)             | `1`                      |

## Development 🛠️

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Judger Locally

Refer to [example.py](example.py) and [main.py](main.py) for more details on usage.

### Testing

Run the following command to execute the test suite:

```bash
pytest --cov=judger
```

For more details, check the [tests](tests) directory.

## License 📜

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
