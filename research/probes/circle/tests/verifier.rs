//! Verifier rejections on the gate fixture from scripts/check_circle_engine.py; no classifier claim.
#![cfg(feature = "prover")]
use hallmark_circle::{prover, sha, verify, Enrollment, Program};
use std::process::Command;
use std::sync::OnceLock;
use stwo::core::fields::m31::P;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::Blake2sMerkleHasher;

const PROGRAM: &str = r#"{"schema":"hallmark.gate-program/1","external":5,"gates":[{"mode":1,"a":2,"b":3,"qa":1,"qb":1,"qm":0,"qk":0},{"mode":2,"a":5,"b":4,"qa":1,"qb":2147483646,"qm":0,"qk":0}]}"#;
const PUBLIC: [u32; 5] = [0, 1, 3, 4, 7];

type Proof = StarkProof<Blake2sMerkleHasher>;

fn fixture() -> &'static (Enrollment, Proof) {
    static PROVED: OnceLock<(Enrollment, Proof)> = OnceLock::new();
    PROVED.get_or_init(|| {
        let program: Program = serde_json::from_str(PROGRAM).unwrap();
        let enrollment = prover::enroll(&program, sha(PROGRAM.as_bytes())).unwrap();
        let proof = prover::prove(&program, &enrollment, &PUBLIC, &[0, 1, 3, 4, 7, 7, 0]).unwrap();
        (enrollment, proof)
    })
}

fn rejects(enrollment: &Enrollment, external: &[u32], message: &str) {
    let error = verify(enrollment, external, fixture().1.clone()).unwrap_err();
    assert_eq!(error.to_string(), message);
}

#[test]
fn library_verify_accepts_fixture_and_rejects_changed_statement() {
    let (enrollment, proof) = fixture();
    verify(enrollment, &PUBLIC, proof.clone()).unwrap();
    rejects(enrollment, &PUBLIC[..4], "invalid public values");
    rejects(enrollment, &[0, 1, 3, 4, 7, 0], "invalid public values");
    rejects(enrollment, &[0, 2, 3, 4, 7], "invalid public values");
    rejects(enrollment, &[0, 1, 3, 4, P], "invalid public values");
    let mut changed = enrollment.clone();
    changed.root.0[0] ^= 1;
    rejects(&changed, &PUBLIC, "preprocessing root mismatch");
}

#[test]
fn verifier_binary_rejects_noncanonical_proof_bytes() {
    let (enrollment, proof) = fixture();
    let dir = std::path::Path::new(env!("CARGO_TARGET_TMPDIR"))
        .join(format!("verify-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let raw = serde_json::to_vec(enrollment).unwrap();
    std::fs::write(dir.join("enrollment.json"), &raw).unwrap();
    std::fs::write(
        dir.join("public.json"),
        serde_json::to_vec(&PUBLIC).unwrap(),
    )
    .unwrap();
    let canonical = serde_json::to_vec(proof).unwrap();
    let run = |bytes: &[u8]| {
        let path = dir.join("proof.json");
        std::fs::write(&path, bytes).unwrap();
        Command::new(env!("CARGO_BIN_EXE_circle-verify"))
            .arg(dir.join("enrollment.json"))
            .arg(sha(&raw))
            .arg(dir.join("public.json"))
            .arg(path)
            .output()
            .unwrap()
    };
    assert!(run(&canonical).status.success());
    // The same proof value with one extra whitespace byte parses but is not canonical.
    let mut spaced = canonical.clone();
    spaced.push(b' ');
    let output = run(&spaced);
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("noncanonical proof encoding"));
    std::fs::remove_dir_all(&dir).unwrap();
}
