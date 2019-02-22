VENV_DIR=../../venv
REQUIREMENTS=../../../requirements.txt
SAMPLE=iqa_one_router_messaging_sample.py

all: local
.PHONY: clean venv clients run run-container local ssh docker

clean:
	# Useful when you have old venv
	@echo "Removing virtual env: $(VENV_DIR)"
	rm -rf $(VENV_DIR) || true
	
venv: clean
	@echo "Creating virtual env: $(VENV_DIR)"
	virtualenv -p python3.6 $(VENV_DIR)
	. $(VENV_DIR)/bin/activate && pip install -r $(REQUIREMENTS)

clients:
	@echo "Executing client containers (cli-java, cli-proton-python and cli-rhea)"
	@docker run -itd --name cli-java rhmessagingqe/cli-java 2> /dev/null || docker start cli-java || true
	@docker run -itd --name cli-proton-python rhmessagingqe/cli-proton-python 2> /dev/null || docker start cli-proton-python || true
	@docker run -itd --name cli-rhea rhmessagingqe/cli-rhea:centos7 2> /dev/null || docker start cli-rhea || true

run: clients
	@echo
	@echo "Running: python $(SAMPLE)"
	@echo "Read the inventory file for more information"
	@echo
	@[[ -d $(VENV_DIR) ]] || echo -en "Virtual env does not exist: $(VENV_DIR)\nRun: make venv\n"
	@. $(VENV_DIR)/bin/activate && python $(SAMPLE) $(INVENTORY)

run-container:
	@echo "Executing dispatch router as a local container named 'router1'"
	@docker run -itd --name router1 rhmessagingqe/qpid-dispatch:ubuntu1804 2> /dev/null || true

local: INVENTORY=inventory_local.yml
local: run

ssh: INVENTORY=inventory_ssh.yml
ssh: run

docker: INVENTORY=inventory_docker.yml
docker: run-container run
	@echo
	@echo "Note: This sample started four containers named:"
	@echo "      - router1"
	@echo "      - cli-java"
	@echo "      - cli-proton-python"
	@echo "      - cli-rhea"
	@echo "      Please stop / remove them as needed."
