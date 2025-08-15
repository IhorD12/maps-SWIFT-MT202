# Contributing

Thanks for taking an interest in improving this prototype. Quick start:

- Install Node.js 18+ and Python 3.10+.
- Install Node deps:

```bash
npm ci
```

- Install Python deps:

```bash
pip3 install -r requirements.txt
```

- Run Hardhat tests:

```bash
npx hardhat test
```

- Run Python scripts (examples):

```bash
python3 -m ml.generate_and_train
python3 -m offchain.reconcile
```

Please open PRs against `main` and include tests for new behavior.
