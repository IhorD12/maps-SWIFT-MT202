// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title MT202Settlement
 * @dev This contract manages the settlement of MT202-like financial messages on-chain.
 * It handles the creation of settlement intents, tracks their status, and facilitates
 * a reconciliation process.
 */
contract MT202Settlement {
    address public owner;
    IERC20 public settlementToken;

    enum Status {
        None,
        IntentCreated,
        OnChainSettled,
        ConfirmedReconciled,
        Dispute
    }

    struct SettlementIntent {
        bytes32 instructionId; // :20: transaction_reference
        address payer;
        address payee;
        uint256 amount;
        string currency;
        uint256 valueDate;
        Status status;
        string orderingInstitution;
        string beneficiaryInstitution;
    }

    mapping(bytes32 => SettlementIntent) public settlementIntents;
    mapping(bytes32 => bool) public processedInstructionIds;

    event IntentCreated(
        bytes32 indexed instructionId,
        address indexed payer,
        address indexed payee,
        uint256 amount,
        string currency,
        uint256 valueDate
    );

    event OnChainSettled(bytes32 indexed instructionId, uint256 settledAmount);
    event ConfirmedReconciled(bytes32 indexed instructionId);
    event DisputeRaised(bytes32 indexed instructionId, string reason);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not the contract owner");
        _;
    }

    constructor(address _tokenAddress) {
        owner = msg.sender;
        settlementToken = IERC20(_tokenAddress);
    }

    /**
     * @dev Creates a new settlement intent. Serves as the on-chain representation of an MT202.
     * Idempotency is ensured by checking the instructionId.
     */
    function createSettlementIntent(
        bytes32 _instructionId,
        address _payer,
        address _payee,
        uint256 _amount,
        string memory _currency,
        uint256 _valueDate,
        string memory _orderingInstitution,
        string memory _beneficiaryInstitution
    ) external onlyOwner {
        require(!processedInstructionIds[_instructionId], "Intent already processed");

        settlementIntents[_instructionId] = SettlementIntent({
            instructionId: _instructionId,
            payer: _payer,
            payee: _payee,
            amount: _amount,
            currency: _currency,
            valueDate: _valueDate,
            status: Status.IntentCreated,
            orderingInstitution: _orderingInstitution,
            beneficiaryInstitution: _beneficiaryInstitution
        });
        processedInstructionIds[_instructionId] = true;

        emit IntentCreated(_instructionId, _payer, _payee, _amount, _currency, _valueDate);
    }

    /**
     * @dev Marks an intent as settled on-chain. In a real scenario, this could trigger
     * the actual fund movement. Here we simulate it.
     */
    function settleIntent(bytes32 _instructionId) external onlyOwner {
        SettlementIntent storage intent = settlementIntents[_instructionId];
        require(intent.status == Status.IntentCreated, "Intent not in created state");

        // In a real implementation, a transfer from the payer's pre-funded account
        // held by the contract would happen here. For this prototype, we'll just
        // check if the contract has enough balance to cover the settlement.
        // The actual debit/credit is assumed to happen off-chain or via another mechanism.
        require(settlementToken.balanceOf(address(this)) >= intent.amount, "Insufficient contract balance for settlement");

        intent.status = Status.OnChainSettled;
        emit OnChainSettled(_instructionId, intent.amount);
    }

    /**
     * @dev Confirms that the off-chain records are reconciled with the on-chain state.
     */
    function confirmReconciliation(bytes32 _instructionId) external onlyOwner {
        SettlementIntent storage intent = settlementIntents[_instructionId];
        require(intent.status == Status.OnChainSettled, "Intent not settled yet");
        intent.status = Status.ConfirmedReconciled;
        emit ConfirmedReconciled(_instructionId);
    }

    /**
     * @dev Raises a dispute for an intent if a discrepancy is found.
     */
    function raiseDispute(bytes32 _instructionId, string memory _reason) external onlyOwner {
        SettlementIntent storage intent = settlementIntents[_instructionId];
        require(
            intent.status == Status.OnChainSettled || intent.status == Status.ConfirmedReconciled,
            "Intent not in a state that can be disputed"
        );
        intent.status = Status.Dispute;
        emit DisputeRaised(_instructionId, _reason);
    }
}
