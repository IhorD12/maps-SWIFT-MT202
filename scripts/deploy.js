import { ethers } from "hardhat";

async function main() {
  console.log("Deploying contracts...");

  const [owner] = await ethers.getSigners();

  // Deploy MockToken
  const MockTokenFactory = await ethers.getContractFactory("MockToken");
  const mockToken = await MockTokenFactory.deploy("Mock Token", "MTK");
  await mockToken.waitForDeployment();
  console.log("MockToken deployed to:", mockToken.target);

  // Deploy MT202Settlement
  const MT202SettlementFactory = await ethers.getContractFactory("MT202Settlement");
  const mt202Settlement = await MT202SettlementFactory.deploy(mockToken.target);
  await mt202Settlement.waitForDeployment();
  console.log("MT202Settlement deployed to:", mt202Settlement.target);

  // Mint tokens to the settlement contract
  const mintAmount = ethers.parseEther("10000");
  await mockToken.mint(mt202Settlement.target, mintAmount);
  console.log(`Minted ${ethers.formatEther(mintAmount)} MTK to the settlement contract.`);

  // --- Verification ---
  console.log("\n--- Running Verification Checks ---");

  // 1. Create a settlement intent
  const instructionId = ethers.encodeBytes32String("verify-inst-1");
  const amount = ethers.parseEther("150");
  const valueDate = Math.floor(Date.now() / 1000);

  console.log("\n1. Creating settlement intent...");
  try {
    const tx = await mt202Settlement.createSettlementIntent(
      instructionId,
      owner.address, // payer
      "0x1234567890123456789012345678901234567890", // payee
      amount,
      "USD",
      valueDate,
      "VERIFY_ORDER_BANK",
      "VERIFY_BENE_BANK"
    );
    const receipt = await tx.wait();
    const event = receipt.logs.find(log => log.fragment.name === 'IntentCreated');
    if (event) {
        console.log("✅ SUCCESS: IntentCreated event emitted.");
    } else {
        console.log("❌ FAILURE: IntentCreated event not emitted.");
    }
  } catch (e) {
    console.error("❌ FAILURE: Creating intent failed:", e.message);
  }

  // 2. Check intent state
  console.log("\n2. Checking intent state...");
  const intent = await mt202Settlement.settlementIntents(instructionId);
  if (intent.status === 1n) { // 1n for BigInt comparison
      console.log("✅ SUCCESS: Intent status is IntentCreated.");
  } else {
      console.log(`❌ FAILURE: Intent status is not IntentCreated (actual: ${intent.status})`);
  }

  // 3. Settle the intent
  console.log("\n3. Settling the intent...");
  try {
      const tx = await mt202Settlement.settleIntent(instructionId);
      await tx.wait();
      console.log("✅ SUCCESS: settleIntent transaction succeeded.");
  } catch(e) {
      console.error("❌ FAILURE: settleIntent failed:", e.message);
  }
  const settledIntent = await mt202Settlement.settlementIntents(instructionId);
   if (settledIntent.status === 2n) {
      console.log("✅ SUCCESS: Intent status is OnChainSettled.");
  } else {
      console.log(`❌ FAILURE: Intent status is not OnChainSettled (actual: ${settledIntent.status})`);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
