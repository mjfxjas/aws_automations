# Contributing to AWS Automations

## Development Setup

1. Clone the repository
2. Create virtual environment: `python3 -m venv .venv`
3. Activate environment: `source .venv/bin/activate`
4. Install in development mode: `pip install -e .[dev]`

## Running Tests

```bash
python -m pytest
```

## Code Style

- Use Black for formatting: `black .`
- Run linting: `flake8 aws_automations/`
- Type checking: `mypy aws_automations/`

## Adding New Services

1. Create new module in `aws_automations/`
2. Follow existing patterns (dry-run, config-driven, batched operations)
3. Add service config to `config.example.yaml`
4. Update `main.py` to include new service
5. Add tests in `tests/`

## Safety Guidelines

- Always default to dry-run mode
- Include comprehensive safety checks
- Use AWS pagination for large datasets
- Handle AWS API errors gracefully
- Log all operations clearly