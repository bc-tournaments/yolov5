import pathlib
import subprocess
import sys
import unittest

from torch.testing._internal.common_utils import IS_IN_CI, IS_LINUX, TestCase, run_tests

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

try:
    # Just in case PyTorch was not built in 'develop' mode
    sys.path.append(str(REPO_ROOT))
    from tools.stats.scribe import rds_write, register_rds_schema
except ImportError:
    register_rds_schema = None
    rds_write = None


# these tests could eventually be changed to fail if the import/init
# time is greater than a certain threshold, but for now we just use them
# as a way to track the duration of `import torch` in our ossci-metrics
# S3 bucket (see tools/stats/print_test_stats.py)
class TestImportTime(TestCase):
    def test_time_import_torch(self):
        TestCase.runWithPytorchAPIUsageStderr("import torch")

    def test_time_cuda_device_count(self):
        TestCase.runWithPytorchAPIUsageStderr(
            "import torch; torch.cuda.device_count()",
        )

    @unittest.skipIf(not IS_LINUX, "Memory test is only implemented for Linux")
    @unittest.skipIf(not IS_IN_CI, "Memory test only runs in CI")
    def test_peak_memory(self):
        def profile(module, name):
            command = f"import {module}; import resource; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)"
            result = subprocess.run(
                [sys.executable, "-c", command],
                stdout=subprocess.PIPE,
            )
            max_rss = int(result.stdout.decode().strip())

            return {
                "test_name": name,
                "peak_memory_bytes": max_rss,
            }

        data = profile("torch", "pytorch")
        baseline = profile("sys", "baseline")
        rds_write(
            "import_stats", [data, baseline]
        )


if __name__ == "__main__":
    if register_rds_schema and IS_IN_CI:
        register_rds_schema(
            "import_stats",
            {
                "test_name": "string",
                "peak_memory_bytes": "int",
                "time_ms": "int",
            },
        )

    run_tests()
