//! Fixed arithmetic circuit AIR. No VM, classifier support or qualification is implied.
//! Adapts STWO's Apache-2.0 PLONK example; Hallmark changes are listed in NOTICE.upstream.
use num_traits::{One, Zero};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;
use stwo::core::air::Component;
use stwo::core::channel::{Blake2sChannel, Channel};
use stwo::core::fields::m31::{M31, P};
use stwo::core::fields::qm31::SecureField;
use stwo::core::fri::FriConfig;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::proof::StarkProof;
use stwo::core::vcs::blake2_hash::Blake2sHash;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sMerkleChannel, Blake2sMerkleHasher};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    relation, EvalAtRow, FrameworkComponent, FrameworkEval, RelationEntry, TraceLocationAllocator,
};

pub type Error = Box<dyn std::error::Error>;
pub type Result<T> = std::result::Result<T, Error>;
pub const N_PRE: usize = 11;
pub const MAX_LOG: u32 = 22;
pub const COLS: [&str; N_PRE] = [
    "a", "b", "c", "fanout", "qa", "qb", "qm", "qk", "qout", "active", "write",
];

pub fn config(log_size: u32) -> PcsConfig {
    PcsConfig {
        pow_bits: 16,
        fri_config: FriConfig::new(5, 4, 80, 1),
        lifting_log_size: Some(log_size + 4),
    }
}
pub fn id(i: usize) -> PreProcessedColumnId {
    PreProcessedColumnId {
        id: format!("hallmark_gate_{}", COLS[i]),
    }
}
pub fn sha(raw: &[u8]) -> String {
    format!("{:x}", Sha256::digest(raw))
}
pub fn read(path: &Path, max: u64) -> Result<Vec<u8>> {
    let info = std::fs::symlink_metadata(path)?;
    if !info.is_file() || info.len() > max {
        return Err("unsafe or oversized file".into());
    }
    let data = std::fs::read(path)?;
    if data.len() as u64 != info.len() || data.len() as u64 > max {
        return Err("changed input file".into());
    }
    Ok(data)
}
pub fn write<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    use std::io::Write;
    let data = serde_json::to_vec(value)?;
    std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?
        .write_all(&data)?;
    Ok(())
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gate {
    pub mode: u32, // 0 private input; 1 arithmetic output; 2 assertion with zero output.
    pub a: u32,
    pub b: u32,
    pub qa: u32,
    pub qb: u32,
    pub qm: u32,
    pub qk: u32,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Program {
    pub schema: String,
    pub external: usize,
    pub gates: Vec<Gate>,
}
impl Program {
    pub fn validate(&self) -> Result<()> {
        if self.schema != "hallmark.gate-program/1"
            || !(2..=1024).contains(&self.external)
            || self.gates.is_empty()
            || self.gates.len() > (1 << MAX_LOG)
        {
            return Err("unsupported program size or schema".into());
        }
        for (i, g) in self.gates.iter().enumerate() {
            let c = (self.external + i) as u32;
            if g.mode > 2
                || g.a >= c
                || g.b >= c
                || [g.qa, g.qb, g.qm, g.qk].into_iter().any(|x| x >= P)
            {
                return Err("noncanonical gate, cycle or field coefficient".into());
            }
            if g.mode == 0 && [g.a, g.b, g.qa, g.qb, g.qm, g.qk] != [0; 6] {
                return Err("malformed private input row".into());
            }
        }
        Ok(())
    }
    pub fn log_size(&self) -> u32 {
        self.gates.len().next_power_of_two().trailing_zeros().max(6)
    }
    pub fn multiplicities(&self) -> Vec<u32> {
        let mut m = vec![0; self.external + self.gates.len()];
        for g in &self.gates {
            m[g.a as usize] += 1;
            m[g.b as usize] += 1;
        }
        m
    }
    pub fn preprocessing(&self) -> [Vec<M31>; N_PRE] {
        let size = 1usize << self.log_size();
        let m = self.multiplicities();
        let mut cols: [Vec<M31>; N_PRE] = std::array::from_fn(|_| vec![M31::zero(); size]);
        for (i, g) in self.gates.iter().enumerate() {
            let c = self.external + i;
            let row = [
                g.a,
                g.b,
                c as u32,
                m[c],
                g.qa,
                g.qb,
                g.qm,
                g.qk,
                u32::from(g.mode == 1),
                1,
                u32::from(g.mode != 2),
            ];
            for j in 0..N_PRE {
                cols[j][i] = M31(row[j]);
            }
        }
        cols
    }
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Enrollment {
    pub schema: String,
    pub program_sha256: String,
    pub log_size: u32,
    pub external_multiplicities: Vec<u32>,
    pub root: Blake2sHash,
    pub pcs: PcsConfig,
}
impl Enrollment {
    pub fn validate(&self) -> Result<()> {
        if self.schema != "hallmark.circle-enrollment/1"
            || !(6..=MAX_LOG).contains(&self.log_size)
            || !(2..=1024).contains(&self.external_multiplicities.len())
            || self.pcs != config(self.log_size)
            || self.program_sha256.len() != 64
            || !self
                .program_sha256
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            || self.external_multiplicities.iter().any(|&m| m >= P)
        {
            return Err("unsupported caller enrollment".into());
        }
        Ok(())
    }
}
relation!(Wires, 2);
#[derive(Clone)]
pub struct GateEval {
    pub log_size: u32,
    pub wires: Wires,
    pub claimed_sum: SecureField,
}
impl FrameworkEval for GateEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }
    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size + 1
    }
    fn evaluate<E: EvalAtRow>(&self, mut e: E) -> E {
        let p: Vec<_> = (0..N_PRE)
            .map(|i| e.get_preprocessed_column(id(i)))
            .collect();
        let a = e.next_trace_mask();
        let b = e.next_trace_mask();
        let c = e.next_trace_mask();
        let product = e.next_trace_mask();
        // Keep selectors and LogUp constraints quadratic for the framework's trace-domain quotient.
        e.add_constraint(product.clone() - a.clone() * b.clone());
        e.add_constraint(
            p[6].clone() * product
                + p[4].clone() * a.clone()
                + p[5].clone() * b.clone()
                + p[7].clone()
                - p[8].clone() * c.clone(),
        );
        e.add_constraint((p[9].clone() - p[10].clone()) * c.clone());
        for v in [a.clone(), b.clone(), c.clone()] {
            e.add_constraint((E::F::one() - p[9].clone()) * v);
        }
        e.add_to_relation(RelationEntry::new(
            &self.wires,
            p[9].clone().into(),
            &[p[0].clone(), a],
        ));
        e.add_to_relation(RelationEntry::new(
            &self.wires,
            p[9].clone().into(),
            &[p[1].clone(), b],
        ));
        e.add_to_relation(RelationEntry::new(
            &self.wires,
            (-p[3].clone()).into(),
            &[p[2].clone(), c],
        ));
        e.finalize_logup();
        e
    }
}
pub fn component(log_size: u32, wires: Wires, sum: SecureField) -> FrameworkComponent<GateEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(
            &(0..N_PRE).map(id).collect::<Vec<_>>(),
        ),
        GateEval {
            log_size,
            wires,
            claimed_sum: sum,
        },
        sum,
    )
}
pub fn begin(enrollment: &Enrollment, external: &[u32]) -> Result<Blake2sChannel> {
    enrollment.validate()?;
    if external.len() != enrollment.external_multiplicities.len()
        || external[0] != 0
        || external[1] != 1
        || external.iter().any(|&x| x >= P)
    {
        return Err("invalid public values".into());
    }
    let mut channel = Blake2sChannel::default();
    channel.mix_u32s(
        &serde_json::to_vec(enrollment)?
            .into_iter()
            .map(u32::from)
            .collect::<Vec<_>>(),
    );
    channel.mix_u32s(external);
    Ok(channel)
}
pub fn public_sum(enrollment: &Enrollment, external: &[u32], wires: &Wires) -> SecureField {
    let mut sum = SecureField::zero();
    for (i, (&v, &m)) in external
        .iter()
        .zip(&enrollment.external_multiplicities)
        .enumerate()
    {
        if m != 0 {
            let q: SecureField = wires.0.combine(&[M31(i as u32), M31(v)]);
            sum += SecureField::from(M31(m)) / q;
        }
    }
    sum
}
pub fn validate_proof(proof: &StarkProof<Blake2sMerkleHasher>, log_size: u32) -> Result<()> {
    let good = |v: &SecureField| v.to_m31_array().iter().all(|x| x.0 < P);
    if proof.config != config(log_size)
        || proof.commitments.len() != 4
        || proof.sampled_values.len() != 4
        || proof.decommitments.len() != 4
        || proof.queried_values.len() != 4
    {
        return Err("unsupported proof shape or parameters".into());
    }
    if proof
        .sampled_values
        .iter()
        .flatten()
        .flatten()
        .any(|v| !good(v))
        || proof
            .queried_values
            .iter()
            .flatten()
            .flatten()
            .any(|v| v.0 >= P)
        || proof
            .fri_proof
            .first_layer
            .fri_witness
            .iter()
            .any(|v| !good(v))
        || proof
            .fri_proof
            .inner_layers
            .iter()
            .any(|l| l.fri_witness.iter().any(|v| !good(v)))
        || proof.fri_proof.last_layer_poly.iter().any(|v| !good(v))
    {
        return Err("noncanonical proof field".into());
    }
    Ok(())
}
pub fn verify(
    enrollment: &Enrollment,
    external: &[u32],
    proof: StarkProof<Blake2sMerkleHasher>,
) -> Result<()> {
    enrollment.validate()?;
    validate_proof(&proof, enrollment.log_size)?;
    if proof.commitments[0] != enrollment.root {
        return Err("preprocessing root mismatch".into());
    }
    let mut channel = begin(enrollment, external)?;
    let scheme =
        &mut CommitmentSchemeVerifier::<Blake2sMerkleChannel>::new(config(enrollment.log_size));
    scheme.commit(
        enrollment.root,
        &vec![enrollment.log_size; N_PRE],
        &mut channel,
    );
    scheme.commit(
        proof.commitments[1],
        &vec![enrollment.log_size; 4],
        &mut channel,
    );
    let wires = Wires::draw(&mut channel);
    let sum = public_sum(enrollment, external, &wires);
    let air = component(enrollment.log_size, wires, sum);
    let sizes = air.trace_log_degree_bounds();
    scheme.commit(proof.commitments[2], &sizes[2], &mut channel);
    stwo::core::verifier::verify(&[&air], &mut channel, scheme, proof)?;
    Ok(())
}

#[cfg(feature = "prover")]
pub mod prover;

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn quadratic_air_uses_one_lifting_domain_and_fixed_security_parameters() {
        let log = 6;
        assert_eq!(config(log).lifting_log_size, Some(log + 4));
        assert_eq!(config(log).fri_config.log_blowup_factor, 4);
        let mut enrollment = Enrollment {
            schema: "hallmark.circle-enrollment/1".into(),
            program_sha256: "0".repeat(64),
            log_size: log,
            external_multiplicities: vec![1, 1],
            root: Blake2sHash([0; 32]),
            pcs: config(log),
        };
        assert!(enrollment.validate().is_ok());
        enrollment.pcs.pow_bits = 0;
        assert!(enrollment.validate().is_err());
    }
    #[test]
    fn program_rejects_cycles_and_noncanonical_field_coefficients() {
        let mut p = Program {
            schema: "hallmark.gate-program/1".into(),
            external: 2,
            gates: vec![Gate {
                mode: 1,
                a: 0,
                b: 1,
                qa: 1,
                qb: 1,
                qm: 0,
                qk: 0,
            }],
        };
        assert!(p.validate().is_ok());
        assert_eq!(p.multiplicities(), vec![1, 1, 0]);
        p.gates[0].a = 2;
        assert!(p.validate().is_err());
        p.gates[0].a = 0;
        p.gates[0].qa = P;
        assert!(p.validate().is_err());
    }
}
