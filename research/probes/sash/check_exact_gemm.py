"""Check SASH's integer GEMM against int64, including values beyond float32."""

import torch
from harness.witness.quant import int_gemm_exact


def main():
    cases = [
        ([127] * 64, [127] * 64, 127 * 127 * 64),
        ([2047] * 9, [1023] * 9, 2047 * 1023 * 9),
        ([-2047] * 9, [1023] * 9, 2047 * 1023 * 9),
        ([2047] * 9 + [-2047] * 8, [1023] * 17, 2047 * 1023 * 17),
    ]
    for left, right, bound in cases:
        a = torch.tensor([left], dtype=torch.int64)
        b = torch.tensor(right, dtype=torch.int64).reshape(-1, 1)
        expected = a @ b
        actual = int_gemm_exact(a.float(), b.float(), bound)
        assert torch.equal(actual.double(), expected.double()), (actual, expected)
    print(f"{len(cases)} exact integer GEMM cases passed")


if __name__ == "__main__":
    main()
