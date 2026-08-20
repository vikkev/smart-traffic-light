import pytest
import sys

res = pytest.main(['-q'])
print('exitcode', res)
sys.exit(res)
