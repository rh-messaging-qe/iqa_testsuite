# iQA Test suites

## Description

Project iQA-testsuite include separate test suites for Messaging.

### Ideas

1) Every test suite should use messaging_abstration API for writing tests.
It not depends on which exactly component you want to use under test.

2) Components for test integration with end software.
Under (messaging_components) setup under conftest.py (with iteration way?) 
Or under not yet existing plugin for py.test

3) Test suites is based on py.test tests runner but can be used any framework.

4) Also get possibility for exactly end testing without messaging_abstraction API.

Please read readme and install requirements.txt before running

## Needed steps

1. Prepare/Deploy required topology (compatible with test suite)
2. Describe the topology Inventory file (we chose compatibility with Ansible Inventory)
3. Related to test runner (Write conftest.py where is also needed describe parts from Ansible Inventory)
    - Fixture for broker, client, router
4. Write tests (with messgaging-abstraction call)

It's designed for testing messaging services.

## Objectives

- Modular
- Scalable
- Abstract

## Dependency and projects

Every test suite can have different dependency.
Read README.md for every test-suite

On these projects iqa-testsuite depends:
   
### (messaging_abstract) Messaging Abstraction aka. AMOM (Abstraction Messaging Of Middleware)

- Abstract classes
- Protocols
- Message
- Client 
    - Sender
    - Receiver
    - Connector
- Broker
- Router
- Node

### (messaging_components) Messaging Components

It's based on messaging_abstract.

#### Brokers 

- Artemis
- QPID

#### Routers

- Qpid Dispatch
 

#### Clients

- Python proton
- CLI (RHEA, Python Proton, JMS)

### (iqa_common)

Common classes methods for this test suite

- IQA Instance
- Node
  - Execution
  - 
#### IQA Instance

Instance know facts about topology. Thought instance is possible go to node in topology or direct access to components.
The instance should verify compatibility your inventory with test suite requirements.

## Running test suites
### Prepare:
```bash
# Create virtual environment
virtualenv3 venv

# Activate virtual environment 
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```
### Temporary dependency installation
```bash
mkdir dependency
git clone https://github.com/rh-messaging-qe/messaging_abstract.git
git clone https://github.com/rh-messaging-qe/messaging_components.git
git clone https://github.com/rh-messaging-qe/iqa_common.git

cd messaging_abstract;    python setup.py install; cd ..
cd messaging_components;  python setup.py install; cd ..
cd iqa_common;            python setup.py install; cd ..
```

### Options
#### Inventory
Path to Inventory with hosts and facts.
IQA Inventory is compatible with Ansible Inventory.

```bash
--inventory ${path_to_inventory}
```

### Run:
Need to run from main conftest.py test-suite root dir.

```bash
./venv/bin/py.test ${test_suite_dir} \
--inventory /path/to/inventory
```

# TODO
- Inventory
- IQA Instance
- xtlog
    - pytest way -> implement pytest-logging/pytest-logger