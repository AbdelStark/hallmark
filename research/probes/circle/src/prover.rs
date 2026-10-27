//! Adapts STWO's Apache-2.0 PLONK example; adds fixed multiplicities and quadratic LogUp.
use crate::*;
use stwo::core::poly::circle::CanonicCoset;
use stwo::prover::backend::simd::column::BaseColumn;
use stwo::prover::backend::simd::m31::LOG_N_LANES;
use stwo::prover::backend::simd::qm31::PackedSecureField;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::BitReversedOrder;
use stwo::prover::CommitmentSchemeProver;
use stwo_constraint_framework::LogupTraceGenerator;

type Evaluation = CircleEvaluation<SimdBackend, M31, BitReversedOrder>;
fn eval(log: u32, col: BaseColumn) -> Evaluation {
    CircleEvaluation::new(CanonicCoset::new(log).circle_domain(), col)
}
fn columns(program: &Program) -> Vec<BaseColumn> {
    program
        .preprocessing()
        .into_iter()
        .map(|c| c.into_iter().collect())
        .collect()
}
fn twiddles(log: u32) -> stwo::prover::poly::twiddles::TwiddleTree<SimdBackend> {
    SimdBackend::precompute_twiddles(
        CanonicCoset::new(config(log).lifting_log_size.unwrap())
            .circle_domain()
            .half_coset,
    )
}

pub fn enroll(program: &Program, program_sha256: String) -> Result<Enrollment> {
    let started = std::time::Instant::now();
    program.validate()?;
    let log = program.log_size();
    let tw = twiddles(log);
    let channel = &mut Blake2sChannel::default();
    let mut scheme = CommitmentSchemeProver::<_, Blake2sMerkleChannel>::new(config(log), &tw);
    let mut tree = scheme.tree_builder();
    tree.extend_evals(columns(program).into_iter().map(|c| eval(log, c)).collect());
    tree.commit(channel);
    eprintln!(
        "{}",
        serde_json::json!({"schema_id":"hallmark.circle-engine-timing/1", "command":"enroll", "preprocessing_seconds":started.elapsed().as_secs_f64()})
    );
    Ok(Enrollment {
        schema: "hallmark.circle-enrollment/1".into(),
        program_sha256,
        log_size: log,
        external_multiplicities: program.multiplicities()[..program.external].to_vec(),
        root: scheme.trees[0].commitment.root(),
        pcs: config(log),
    })
}

pub fn prove(
    program: &Program,
    enrollment: &Enrollment,
    external: &[u32],
    values: &[u32],
) -> Result<StarkProof<Blake2sMerkleHasher>> {
    let mut stages = std::collections::BTreeMap::new();
    let mut last = std::time::Instant::now();
    let mut tick = |name| {
        let now = std::time::Instant::now();
        stages.insert(name, now.duration_since(last).as_secs_f64());
        last = now;
    };
    program.validate()?;
    let log = program.log_size();
    if log != enrollment.log_size
        || program.multiplicities()[..program.external] != enrollment.external_multiplicities
        || values.len() != program.external + program.gates.len()
        || values[..program.external] != *external
        || values.iter().any(|&v| v >= P)
    {
        return Err("witness/program/public dimensions mismatch".into());
    }
    let tw = twiddles(log);
    let mut channel = begin(enrollment, external)?;
    let mut scheme = CommitmentSchemeProver::<_, Blake2sMerkleChannel>::new(config(log), &tw);
    scheme.set_store_polynomials_coefficients();
    tick("admission_twiddles_and_transcript");
    let pre = columns(program);
    let mut tree = scheme.tree_builder();
    tree.extend_evals(pre.iter().cloned().map(|c| eval(log, c)).collect());
    tree.commit(&mut channel);
    if scheme.trees[0].commitment.root() != enrollment.root {
        return Err("program preprocessing differs from enrollment".into());
    }
    tick("preprocessing_and_model_commitment");
    let mut scalar: [Vec<M31>; 4] = std::array::from_fn(|_| vec![M31::zero(); 1 << log]);
    for (i, g) in program.gates.iter().enumerate() {
        scalar[0][i] = M31(values[g.a as usize]);
        scalar[1][i] = M31(values[g.b as usize]);
        scalar[2][i] = M31(values[program.external + i]);
        scalar[3][i] = scalar[0][i] * scalar[1][i];
    }
    let base: Vec<BaseColumn> = scalar
        .into_iter()
        .map(|v| v.into_iter().collect())
        .collect();
    tick("base_trace_generation");
    let mut tree = scheme.tree_builder();
    tree.extend_evals(base.iter().cloned().map(|c| eval(log, c)).collect());
    tree.commit(&mut channel);
    tick("base_trace_commitment");
    let wires = Wires::draw(&mut channel);
    let mut interaction = LogupTraceGenerator::new(log);
    for input in 0..2 {
        let mut column = interaction.new_col();
        for row in 0..(1 << (log - LOG_N_LANES)) {
            let q: PackedSecureField = wires
                .0
                .combine(&[pre[input].data[row], base[input].data[row]]);
            column.write_frac(row, pre[9].data[row].into(), q);
        }
        column.finalize_col();
    }
    let mut column = interaction.new_col();
    for row in 0..(1 << (log - LOG_N_LANES)) {
        let qc: PackedSecureField = wires.0.combine(&[pre[2].data[row], base[2].data[row]]);
        column.write_frac(row, (-pre[3].data[row]).into(), qc);
    }
    column.finalize_col();
    let (trace, sum) = interaction.finalize_last();
    if sum != public_sum(enrollment, external, &wires) {
        return Err("wire/public multiset balance failed".into());
    }
    tick("interaction_generation");
    let mut tree = scheme.tree_builder();
    tree.extend_evals(trace);
    tree.commit(&mut channel);
    tick("interaction_commitment");
    #[cfg(test)]
    {
        let polys = scheme.trees.as_ref().map(|tree| {
            tree.polynomials
                .iter()
                .map(|p| p.coeffs.clone().unwrap())
                .collect()
        });
        stwo_constraint_framework::assert_constraints_on_polys(
            &polys,
            CanonicCoset::new(log),
            |e| {
                GateEval {
                    log_size: log,
                    wires: wires.clone(),
                    claimed_sum: sum,
                }
                .evaluate(e);
            },
            sum,
        );
    }
    let air = component(log, wires, sum);
    let proof = stwo::prover::prove(&[&air], &mut channel, scheme)?;
    tick("stark_proving");
    eprintln!(
        "{}",
        serde_json::json!({"schema_id":"hallmark.circle-engine-timing/1", "command":"prove", "stages_seconds":stages})
    );
    Ok(proof)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn arithmetic_proof_roundtrip() {
        let program = Program {
            schema: "hallmark.gate-program/1".into(),
            external: 5,
            gates: vec![
                Gate {
                    mode: 1,
                    a: 2,
                    b: 3,
                    qa: 1,
                    qb: 1,
                    qm: 0,
                    qk: 0,
                },
                Gate {
                    mode: 2,
                    a: 5,
                    b: 4,
                    qa: 1,
                    qb: P - 1,
                    qm: 0,
                    qk: 0,
                },
            ],
        };
        let enrollment = enroll(&program, sha(&serde_json::to_vec(&program).unwrap())).unwrap();
        let public = [0, 1, 3, 4, 7];
        let proof = prove(&program, &enrollment, &public, &[0, 1, 3, 4, 7, 7, 0]).unwrap();
        verify(&enrollment, &public, proof).unwrap();
    }
}
