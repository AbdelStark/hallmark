// Hallmark's fixed gate AIR; field arithmetic and FFT/FRI come from Nitroo/STWO.
#include "fields.cuh"
#include "utils.cuh"

__global__ void pack_kernel(m31 **inputs, m31 **outputs, unsigned n) {
    unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    for (unsigned c = 0; c < 4; ++c)
        outputs[4 * (i % 4) + c][i / 4] = inputs[c][i];
}

extern "C" void hallmark_pack(const m31 **inputs, const m31 **outputs, unsigned n) {
    auto in = clone_to_device<const m31 *>(inputs, 4);
    auto out = clone_to_device<const m31 *>(outputs, 16);
    pack_kernel<<<(n + 255) / 256, 256>>>((m31 **)in, (m31 **)out, n);
    ASSERT_CUDA_SUCCESS(cudaGetLastError());
    ASSERT_CUDA_SUCCESS(cudaDeviceSynchronize());
    cuda_free_memory(in);
    cuda_free_memory(out);
}

__device__ qm31 load(m31 **columns, unsigned col, unsigned row) {
    return {{columns[col][row], columns[col + 1][row]},
            {columns[col + 2][row], columns[col + 3][row]}};
}

__device__ qm31 secure(m31 x) { return {{x, 0}, {0, 0}}; }
__device__ qm31 secure(qm31 x) { return x; }

__global__ void gate_kernel(m31 **pre, m31 **base, m31 **inter, m31 **out,
                           qm31 *powers, m31 *denom, qm31 *params,
                           unsigned log, unsigned eval_log) {
    unsigned row = blockIdx.x * blockDim.x + threadIdx.x;
    if (row >= (1u << eval_log)) return;
    m31 p[11];
    for (unsigned j = 0; j < 11; ++j) p[j] = pre[j][row];
    m31 a = base[0][row], b = base[1][row], c = base[2][row];
    m31 product = base[3][row];
    qm31 acc = {{0, 0}, {0, 0}};
    unsigned k = 0;
    #define CONSTRAINT(x) acc = add(acc, mul(powers[k++], secure(x)))
    CONSTRAINT(sub(product, mul(a, b)));
    CONSTRAINT(sub(add(add(add(mul(p[6], product), mul(p[4], a)),
                           mul(p[5], b)), p[7]), mul(p[8], c)));
    CONSTRAINT(mul(sub(p[9], p[10]), c));
    CONSTRAINT(mul(sub(1u, p[9]), a));
    CONSTRAINT(mul(sub(1u, p[9]), b));
    CONSTRAINT(mul(sub(1u, p[9]), c));
    qm31 previous = {{0, 0}, {0, 0}};
    m31 values[3] = {a, b, c};
    for (unsigned j = 0; j < 3; ++j) {
        qm31 q = sub(add(mul(p[j], params[0]), mul(values[j], params[1])), params[2]);
        qm31 current = load(inter, 4 * j, row);
        qm31 diff = sub(current, previous);
        if (j == 2) {
            unsigned prior = offset_bit_reversed_circle_domain_index(row, log, eval_log, -1);
            diff = add(sub(diff, load(inter, 8, prior)), params[3]);
        }
        m31 multiplicity = j == 2 ? neg(p[3]) : p[9];
        CONSTRAINT(sub(mul(diff, q), qm31{{multiplicity, 0}, {0, 0}}));
        previous = current;
    }
    #undef CONSTRAINT
    qm31 quotient = mul(denom[row >> log], acc);
    out[0][row] = quotient.a.a;
    out[1][row] = quotient.a.b;
    out[2][row] = quotient.b.a;
    out[3][row] = quotient.b.b;
}

extern "C" void hallmark_gate(const m31 **pre, const m31 **base,
                              const m31 **inter, const m31 **out,
                              const qm31 *powers, const m31 *denom,
                              const qm31 *params, unsigned log, unsigned eval_log) {
    auto p = clone_to_device<const m31 *>(pre, 11);
    auto b = clone_to_device<const m31 *>(base, 4);
    auto i = clone_to_device<const m31 *>(inter, 12);
    auto o = clone_to_device<const m31 *>(out, 4);
    auto scalars = clone_to_device<qm31>(const_cast<qm31 *>(params), 4);
    gate_kernel<<<((1u << eval_log) + 255) / 256, 256>>>(
        (m31 **)p, (m31 **)b, (m31 **)i, (m31 **)o,
        (qm31 *)powers, (m31 *)denom, scalars, log, eval_log);
    ASSERT_CUDA_SUCCESS(cudaGetLastError());
    ASSERT_CUDA_SUCCESS(cudaDeviceSynchronize());
    cuda_free_memory(p);
    cuda_free_memory(b);
    cuda_free_memory(i);
    cuda_free_memory(o);
    cuda_free_memory(scalars);
}
