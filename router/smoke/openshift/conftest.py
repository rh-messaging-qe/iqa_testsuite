import os


def pytest_generate_tests(metafunc):
    """
    Iterate through tests with length parameter and make
    sure tests will be executed with 1024 increment.
    """
    if 'length' in metafunc.fixturenames:
        metafunc.parametrize("length", [x*1024 for x in [1, 5, 10]])
