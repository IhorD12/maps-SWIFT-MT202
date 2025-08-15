Changes applied by automation:

- Added `.gitignore`, `.env.example`, `Makefile`, and GitHub Actions workflow (`.github/workflows/ci.yml`).
- Updated `package.json` with name, scripts, and eslint devDependency.
- Fixed `MockToken.sol` constructor (removed erroneous Ownable initialization).
- Fixed JS tests and `scripts/deploy.js` to use `.address` instead of `.target` and standardized id creation.
- Added `CONTRIBUTING.md` and updated `README.md` with testing instructions.

Next suggested improvements (low-risk):
- Add Python unit tests for `offchain/` scripts and run them in CI.
- Add ESlint config and run lint in CI.
- Add Solidity static analysis (slither) to CI.
- Add pre-commit hooks for formatting and simple checks.

