import { expect } from "chai";
import { ethers } from "hardhat";

describe("MT202Settlement", function () {
    let mt202Settlement, mockToken, owner, addr1, addr2;

    beforeEach(async function () {
        [owner, addr1, addr2] = await ethers.getSigners();

        const MockTokenFactory = await ethers.getContractFactory("MockToken");
        mockToken = await MockTokenFactory.deploy("Mock Token", "MTK");

        const MT202SettlementFactory = await ethers.getContractFactory("MT202Settlement");
        mt202Settlement = await MT202SettlementFactory.deploy(mockToken.target);

        await mockToken.mint(mt202Settlement.target, ethers.parseEther("10000"));
    });

    describe("Deployment", function () {
        it("Should set the right owner", async function () {
            expect(await mt202Settlement.owner()).to.equal(owner.address);
        });

        it("Should set the right settlement token", async function () {
            expect(await mt202Settlement.settlementToken()).to.equal(mockToken.target);
        });
    });

    describe("Settlement Intent Management", function () {
        const instructionId = ethers.encodeBytes32String("test-instruction-1");
        const amount = ethers.parseEther("100");
        const valueDate = Math.floor(Date.now() / 1000);

        it("Should allow the owner to create a settlement intent", async function () {
            const tx = await mt202Settlement.createSettlementIntent(
                instructionId,
                addr1.address,
                addr2.address,
                amount,
                "USD",
                valueDate,
                "ORDERING_BANK",
                "BENEFICIARY_BANK"
            );

            await expect(tx)
                .to.emit(mt202Settlement, "IntentCreated")
                .withArgs(instructionId, addr1.address, addr2.address, amount, "USD", valueDate);

            const intent = await mt202Settlement.settlementIntents(instructionId);
            expect(intent.status).to.equal(1); // 1: IntentCreated
        });

        it("Should prevent creating an intent with a duplicate instructionId", async function () {
            await mt202Settlement.createSettlementIntent(
                instructionId,
                addr1.address,
                addr2.address,
                amount,
                "USD",
                valueDate,
                "ORDERING_BANK",
                "BENEFICIARY_BANK"
            );

            await expect(mt202Settlement.createSettlementIntent(
                instructionId,
                addr1.address,
                addr2.address,
                amount,
                "USD",
                valueDate,
                "ORDERING_BANK",
                "BENEFICIARY_BANK"
            )).to.be.revertedWith("Intent already processed");
        });

        it("Should only allow the owner to create intents", async function () {
            await expect(mt202Settlement.connect(addr1).createSettlementIntent(
                instructionId,
                addr1.address,
                addr2.address,
                amount,
                "USD",
                valueDate,
                "ORDERING_BANK",
                "BENEFICIARY_BANK"
            )).to.be.revertedWith("Not the contract owner");
        });
    });

    describe("State Transitions", function () {
        const instructionId = ethers.encodeBytes32String("test-instruction-2");
        const amount = ethers.parseEther("50");
        const valueDate = Math.floor(Date.now() / 1000);

        beforeEach(async function() {
            await mt202Settlement.createSettlementIntent(
                instructionId,
                addr1.address,
                addr2.address,
                amount,
                "EUR",
                valueDate,
                "ORDERING_BANK_2",
                "BENEFICIARY_BANK_2"
            );
        });

        it("Should allow settling a created intent", async function () {
            await expect(mt202Settlement.settleIntent(instructionId))
                .to.emit(mt202Settlement, "OnChainSettled")
                .withArgs(instructionId, amount);

            const intent = await mt202Settlement.settlementIntents(instructionId);
            expect(intent.status).to.equal(2); // 2: OnChainSettled
        });

        it("Should allow confirming a settled intent", async function () {
            await mt202Settlement.settleIntent(instructionId);
            await expect(mt202Settleme_nt.confirmReconciliation(instructionId))
                .to.emit(mt202Settlement, "ConfirmedReconciled")
                .withArgs(instructionId);

            const intent = await mt202Settlement.settlementIntents(instructionId);
            expect(intent.status).to.equal(3); // 3: ConfirmedReconciled
        });

        it("Should allow raising a dispute on a settled intent", async function () {
            await mt202Settlement.settleIntent(instructionId);
            await expect(mt202Settlement.raiseDispute(instructionId, "Amount mismatch"))
                .to.emit(mt202Settlement, "DisputeRaised")
                .withArgs(instructionId, "Amount mismatch");

            const intent = await mt202Settlement.settlementIntents(instructionId);
            expect(intent.status).to.equal(4); // 4: Dispute
        });
    });
});
