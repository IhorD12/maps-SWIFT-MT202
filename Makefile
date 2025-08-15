.PHONY: deps test compile

deps:
	npm ci || true
	pip3 install -r requirements.txt || true

compile:
	npx hardhat compile

test:
	npx hardhat test
