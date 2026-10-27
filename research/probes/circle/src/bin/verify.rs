use hallmark_circle::{read, sha, verify, Enrollment, Error};
use std::path::Path;
fn main() -> Result<(), Error> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 5 {
        return Err("usage: circle-verify enrollment.json expected-enrollment-sha256 public.json proof.json".into());
    }
    let raw = read(Path::new(&a[1]), 65536)?;
    if sha(&raw) != a[2] {
        return Err("caller enrollment pin mismatch".into());
    }
    let enrollment: Enrollment = serde_json::from_slice(&raw)?;
    let external: Vec<u32> = serde_json::from_slice(&read(Path::new(&a[3]), 16384)?)?;
    let raw = read(Path::new(&a[4]), 64 * 1024 * 1024)?;
    let proof = serde_json::from_slice(&raw)?;
    if serde_json::to_vec(&proof)? != raw {
        return Err("noncanonical proof encoding".into());
    }
    verify(&enrollment, &external, proof)?;
    println!(
        "{{\"status\":\"passed\",\"cryptographic_verification\":true,\"qualified_backend\":false}}"
    );
    Ok(())
}
