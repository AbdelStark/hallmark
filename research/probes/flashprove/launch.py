"""The transport starts non-build phases with Python; hand over to the shared bash worker."""

import os

os.execvp("bash", ["bash", "/persist/build_prover.sh"])
