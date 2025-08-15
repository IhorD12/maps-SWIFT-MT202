import solcx
import json
import os
import subprocess

# Define paths
CONTRACTS_DIR = "contracts"
BUILD_DIR = os.path.join("offchain", "build")
NODE_MODULES_DIR = "node_modules"

def compile_contracts():
    """
    Compiles the Solidity contracts using py-solc-x and saves their ABI and bytecode.
    """
    # Ensure the Solidity compiler is available
    try:
        solcx.set_solc_version('v0.8.24', silent=True)
    except solcx.exceptions.SolcNotInstalled:
        print("Solidity compiler v0.8.24 not found. Installing...")
        solcx.install_solc('v0.8.24')
        solcx.set_solc_version('v0.8.24')

    print("Compiling contracts...")

    # Define source files
    source_files = [
        os.path.join(CONTRACTS_DIR, "MT202Settlement.sol"),
        os.path.join(CONTRACTS_DIR, "MockToken.sol")
    ]

    # Compile
    try:
        compiled_sol = solcx.compile_files(
            source_files,
            output_values=["abi", "bin"],
            # Simplify to just allow the root project directory, which contains contracts and node_modules
            allow_paths=["."],
            import_remappings=[f"@openzeppelin={NODE_MODULES_DIR}/@openzeppelin"]
        )

        # Create build directory if it doesn't exist
        os.makedirs(BUILD_DIR, exist_ok=True)

        # Save ABI and bytecode
        for contract_path, contract_data in compiled_sol.items():
            contract_name = os.path.basename(contract_path).split('.sol')[0]
            output_path = os.path.join(BUILD_DIR, f"{contract_name}.json")

            with open(output_path, 'w') as f:
                json.dump({
                    "abi": contract_data['abi'],
                    "bytecode": contract_data['bin']
                }, f, indent=4)
            print(f"  -> Saved artifacts for {contract_name} to {output_path}")

        print("Compilation successful.")
        return True

    except solcx.exceptions.SolcError as e:
        # Correctly handle the exception and print details
        print("Error compiling contracts:")
        if isinstance(e.__cause__, subprocess.CalledProcessError):
            print(f"Return Code: {e.__cause__.returncode}")
            print(f"Stdout: {e.__cause__.stdout.decode('utf-8', 'ignore')}")
            print(f"Stderr: {e.__cause__.stderr.decode('utf-8', 'ignore')}")
        else:
            print(e)
        return False

if __name__ == "__main__":
    compile_contracts()
